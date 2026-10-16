"""Relay bot replies from users' rooms (OMB event stream) to the backend.

Updates are throttled while a reply streams in, and a reply is reported `final` once it
has been quiet for a few seconds, which is when the backend may send a push notification.
"""

import asyncio
import json
import logging
import time

import httpx

from gateway.omb import omb
from gateway.settings import settings

log = logging.getLogger(__name__)


class Relay:
    def __init__(self) -> None:
        self.room_threads: set[str] = set()
        self._pending: dict[str, dict] = {}  # message id -> {thread_id, message, last_change, last_sent}
        self.connected = False
        self.last_event_at: float | None = None

    def watch_thread(self, thread_id: str) -> None:
        self.room_threads.add(thread_id)

    async def load_rooms(self) -> None:
        snap = await omb.snapshot()
        for g in snap.get("groups", []):
            if str(g.get("name", "")).startswith("Bachat · ") and g.get("threadId"):
                self.room_threads.add(g["threadId"])

    async def run(self) -> None:
        while True:
            try:
                await self.load_rooms()
                await self._consume()
            except Exception as exc:  # reconnect on any failure
                self.connected = False
                log.warning("event stream dropped: %s", exc)
            await asyncio.sleep(3)

    async def _consume(self) -> None:
        token = await omb.ensure_token()
        async with httpx.AsyncClient(base_url=settings.omb_url, timeout=httpx.Timeout(None, connect=10)) as c:
            async with c.stream("GET", "/api/events", params={"screens": "off"},
                                headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}) as r:
                if r.status_code == 401:
                    await omb.ensure_token(force=True)
                    raise RuntimeError("unauthorized")
                r.raise_for_status()
                self.connected = True
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        event = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    self.last_event_at = time.time()
                    self._handle(event)

    def _handle(self, event: dict) -> None:
        if event.get("kind") == "group":
            g = event.get("group") or {}
            if str(g.get("name", "")).startswith("Bachat · ") and g.get("threadId"):
                self.room_threads.add(g["threadId"])
            return
        if event.get("kind") != "message":
            return
        thread_id = event.get("threadId")
        msg = event.get("message") or {}
        if thread_id not in self.room_threads or msg.get("role") != "bot":
            return
        tool = msg.get("tool") or {}
        if msg.get("kind") == "activity" and tool.get("terminal") and tool.get("ok") is False:
            # The turn died (model unreachable, timeout ...). Tell the person instead of leaving them waiting.
            self._pending[msg["id"]] = {"thread_id": thread_id, "kind": "error", "sender": "",
                                        "text": str(tool.get("name") or "error"), "last_sent": 0.0,
                                        "last_change": time.time() - settings.relay_final_after_seconds}
            return
        if msg.get("kind") != "text":
            return
        sender = (msg.get("from") or {}).get("name") or (msg.get("sender") or {}).get("name") or ""
        entry = self._pending.setdefault(msg["id"], {"last_sent": 0.0})
        entry.update(thread_id=thread_id, kind="text", text=msg.get("text") or "", sender=sender.split(" · ")[0],
                     last_change=time.time())

    async def flusher(self) -> None:
        """Every second: send changed messages (streaming) and finalise quiet ones."""
        while True:
            await asyncio.sleep(1)
            now = time.time()
            batch, done = [], []
            for mid, e in list(self._pending.items()):
                if "text" not in e:
                    continue
                final = now - e["last_change"] >= settings.relay_final_after_seconds
                if final or e["last_change"] > e["last_sent"]:
                    batch.append({"thread_id": e["thread_id"], "message": {
                        "id": mid, "role": "bot", "kind": e.get("kind", "text"), "text": e["text"], "sender": e["sender"],
                        "final": final}})
                    e["last_sent"] = now
                if final:
                    done.append(mid)
            if not batch:
                continue
            try:
                async with httpx.AsyncClient(timeout=20) as c:
                    r = await c.post(f"{settings.backend_url}/api/internal/omb/events", json=batch,
                                     headers={"x-internal-key": settings.internal_api_key})
                    r.raise_for_status()
                for mid in done:
                    self._pending.pop(mid, None)
            except httpx.HTTPError as exc:
                log.warning("could not deliver %d events to backend: %s", len(batch), exc)


relay = Relay()
