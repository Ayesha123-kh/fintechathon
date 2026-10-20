"""In-app notifications + Web Push (works while the PWA is closed)."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select

from app.core.cache import chat_channel, presence_key, redis
from app.core.config import settings
from app.core.db import scoped_session
from app.models import ChatMessage, Notification, PushSubscription

log = logging.getLogger(__name__)


def _send_one(sub: PushSubscription, payload: str) -> str:
    """Returns 'ok', 'gone' or 'error'."""
    try:
        webpush(
            subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=60 * 60 * 12,
        )
        return "ok"
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            return "gone"
        log.warning("web push failed: %s", exc)
        return "error"


async def notify(
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    url: str = "/dashboard?chat=1",
    push: bool = True,
    only_if_offline: bool = False,
) -> None:
    """Store a notification, show it in the chat as an unread message and push it to the user's devices.

    kind "chat" notifications announce a bot reply that is already in the chat, so they are not repeated there.
    """
    async with scoped_session(user_id, "user") as s:
        note = Notification(user_id=user_id, kind=kind, title=title, body=body, url=url)
        s.add(note)
        if kind != "chat":
            msg = ChatMessage(user_id=user_id, role="bot", sender="Paisave", kind="notification",
                              text=f"**{title}**\n{body}", final=True, created_at=datetime.now(UTC))
            s.add(msg)
            await s.flush()
            await redis.publish(chat_channel(str(user_id)), json.dumps({"type": "message", "message": {
                "id": str(msg.id), "role": "bot", "sender": "Paisave", "text": msg.text, "kind": "notification",
                "final": True, "created_at": msg.created_at.isoformat() if msg.created_at else None}}))
        subs = list((await s.execute(select(PushSubscription))).scalars())
        if only_if_offline and await redis.exists(presence_key(str(user_id))):
            push = False
        if not push or not subs or not settings.vapid_private_key:
            return
        payload = json.dumps({"title": title, "body": body, "url": url, "kind": kind, "tag": kind})
        results = await asyncio.gather(*(asyncio.to_thread(_send_one, sub, payload) for sub in subs))
        gone = [sub.id for sub, res in zip(subs, results, strict=True) if res == "gone"]
        if gone:
            await s.execute(delete(PushSubscription).where(PushSubscription.id.in_(gone)))
        note.pushed = any(r == "ok" for r in results)
