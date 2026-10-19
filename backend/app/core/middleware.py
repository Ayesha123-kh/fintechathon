"""ASGI middleware: request body caps and security headers (plain ASGI, so streaming responses are untouched)."""

from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import limits

MULTIPART_SLACK = 64 * 1024


def body_cap(path: str) -> int:
    """The largest request body each part of the app accepts."""
    if path == "/api/chat/transcribe":
        return limits.VOICE_MAX_BYTES + MULTIPART_SLACK
    if path == "/api/me/avatar":
        return limits.AVATAR_MAX_BYTES + MULTIPART_SLACK
    if path.startswith("/api/internal/"):
        return 4 * 1024 * 1024  # batches of bot replies from the gateway
    if path.startswith("/mcp/"):
        return 1024 * 1024  # bots' tool calls
    return 64 * 1024  # every other API call is a small JSON object


class BodyLimit:
    """Refuse oversized request bodies: by Content-Length before reading, and while streaming when it's absent or
    wrong, so a huge upload is never held in memory or spooled to disk."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        cap = body_cap(scope["path"])
        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > cap):
            await _reply(send, 413, b'{"detail":"request_too_large"}')
            return
        received = 0

        async def limited() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > cap:
                    raise HTTPException(413, "request_too_large")
            return message

        await self.app(scope, limited, send)


API_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-resource-policy", b"same-origin"),
]


class SecurityHeaders:
    """Standard protective headers on every response; API responses are also kept out of caches (financial data)
    unless the endpoint chose its own Cache-Control (the profile photo does)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                present = {k.lower() for k, _ in headers}
                headers += [(k, v) for k, v in API_HEADERS if k not in present]
                if b"cache-control" not in present and scope["path"].startswith("/api/"):
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, with_headers)


async def _reply(send: Send, status: int, body: bytes) -> None:
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
