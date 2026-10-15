import secrets
from typing import Any

from fastapi.encoders import jsonable_encoder
from starlette.types import ASGIApp, Receive, Scope, Send


def out(value: Any) -> Any:
    """Make tool results JSON friendly (Decimal, UUID, datetime)."""
    return jsonable_encoder(value)


class BearerGuard:
    """ASGI wrapper: only callers presenting the configured bearer token reach the MCP app."""

    def __init__(self, app: ASGIApp, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            given = auth[7:] if auth.lower().startswith("bearer ") else ""
            if not given or not secrets.compare_digest(given, self.token):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)
