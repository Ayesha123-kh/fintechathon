"""Relay bot replies from users' rooms (OMB event stream) to the backend.

Updates are throttled while a reply streams in. A reply is reported `final` when the bot's turn ends (OMB posts a
digest), which is when the backend may send a push notification and the chat input unlocks. While a turn runs, the
bot's thinking and tool calls are relayed as live activity, so the person sees progress on long turns instead of a
silent wait that looks like a timeout.
"""

import asyncio
import json
import logging
import time

import httpx

from gateway.omb import omb
from gateway.settings import settings

log = logging.getLogger(__name__)

THINKING_TAIL = 2000  # characters of the latest reasoning kept per thread


class Relay:
    def __init__(self) -> None:
        self.room_threads: set[str] = set()
        self._pending: dict[str, dict] = {}  # message id -> {thread_id, message, last_change, last_sent}
        # thread id -> live turn state: {state, thinking, tool, sender, last_seen, done_at, last_sent}
        self._turns: dict[str, dict] = {}
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

    def _turn(self, thread_id: str, **changes) -> None:
        """Note a sign of life in a room's turn (and what it is doing now)."""
        t = self._turns.setdefault(thread_id, {"state": "idle", "thinking": "", "tool": None, "sender": "",
                                               "done_at": None, "last_sent": 0.0})
        if changes.get("state") not in (None, "idle") and t["state"] == "idle":
            t.update(thinking="", tool=None, done_at=None)  # a new turn starts
        t.update(changes, last_seen=time.time())

    def _handle(self, event: dict) -> None:
        kind = event.get("kind")
        if kind == "group":
            g = event.get("group") or {}
            if str(g.get("name", "")).startswith("Bachat · ") and g.get("threadId"):
                self.room_threads.add(g["threadId"])
            return
        if kind == "runtime":
            self._handle_runtime(event.get("event") or {})
            return
        if kind != "message":
            return
        thread_id = event.get("threadId")
        msg = event.get("message") or {}
        if thread_id not in self.room_threads:
            return
        if msg.get("role") == "user":
            self._turn(thread_id, state="thinking")
            return
        if msg.get("role") != "bot":
            return
        sender = ((msg.get("from") or {}).get("name") or (msg.get("sender") or {}).get("name") or "").split(" · ")[0]
        tool = msg.get("tool") or {}
        if msg.get("kind") == "digest":
            self._turn(thread_id, state="idle", tool=None, done_at=time.time())
            return
        if msg.get("kind") == "activity" and tool.get("terminal") and tool.get("ok") is False:
            # The turn died (model unreachable, timeout ...). Tell the person instead of leaving them waiting.
            self._pending[msg["id"]] = {"thread_id": thread_id, "kind": "error", "sender": "",
                                        "text": str(tool.get("name") or "error"), "last_sent": 0.0, "error": True,
                                        "last_change": time.time()}
            self._turn(thread_id, state="idle", tool=None, done_at=time.time())
            return
        if msg.get("kind") == "activity":
            if tool.get("itemId"):  # a real tool call (not an informational note)
                self._turn(thread_id, state="tool", tool=str(tool.get("name") or ""), sender=sender)
            return
        if msg.get("kind") != "text":
            return
        self._turn(thread_id, state="writing", tool=None, sender=sender)
        entry = self._pending.setdefault(msg["id"], {"last_sent": 0.0})
        entry.update(thread_id=thread_id, kind="text", text=msg.get("text") or "", sender=sender,
                     last_change=time.time())

    def _handle_runtime(self, ev: dict) -> None:
        thread_id = ev.get("threadId")
        if thread_id not in self.room_threads:
            return
        etype = ev.get("type")
        if etype == "turn.completed":
            self._turn(thread_id, state="idle", tool=None, done_at=time.time())
        elif etype == "content.delta" and ev.get("streamKind") == "reasoning_text":
            t = self._turns.get(thread_id) or {}
            thinking = (t.get("thinking", "") if t.get("state") != "idle" else "") + str(ev.get("delta") or "")
            self._turn(thread_id, state="thinking", thinking=thinking[-THINKING_TAIL:])
        elif etype == "content.delta" and ev.get("streamKind") == "assistant_text":
            self._turn(thread_id, state="writing", tool=None)
        elif etype == "turn.started":
            self._turn(thread_id, state="thinking")
        elif thread_id in self._turns and self._turns[thread_id]["state"] != "idle":
            self._turn(thread_id)  # any other runtime event still means the turn is alive

    def _is_final(self, e: dict, now: float) -> bool:
        if e.get("error"):
            return True
        t = self._turns.get(e["thread_id"]) or {}
        if t.get("done_at") and t["done_at"] >= e["last_change"]:
            return True
        # Fallback: nothing at all has happened in this thread for a long time.
        return now - max(e["last_change"], t.get("last_seen", 0.0)) >= settings.relay_final_after_seconds

    async def flusher(self) -> None:
        """Every second: send changed messages (streaming), live turn activity, and finalise finished replies."""
        while True:
            await asyncio.sleep(1)
            now = time.time()
            batch, done = [], []
            for mid, e in list(self._pending.items()):
                if "text" not in e:
                    continue
                final = self._is_final(e, now)
                if final or e["last_change"] > e["last_sent"]:
                    batch.append({"thread_id": e["thread_id"], "message": {
                        "id": mid, "role": "bot", "kind": e.get("kind", "text"), "text": e["text"], "sender": e["sender"],
                        "final": final}})
                    e["last_sent"] = now
                if final:
                    done.append(mid)
            for thread_id, t in list(self._turns.items()):
                if t["last_seen"] > t["last_sent"]:
                    batch.append({"thread_id": thread_id, "status": {
                        "state": t["state"], "thinking": t["thinking"], "tool": t["tool"], "sender": t["sender"]}})
                    t["last_sent"] = now
                if t["state"] == "idle" and now - t["last_seen"] > 600:
                    self._turns.pop(thread_id, None)
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
