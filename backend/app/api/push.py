from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import enforce
from app.core.config import settings
from app.core.db import system_session
from app.core.deps import Principal, own_db, user_principal
from app.models import PushSubscription
from app.services.notify import notify, push_endpoint_ok

router = APIRouter(prefix="/push", tags=["push"])

MAX_DEVICES = 10  # per person; the oldest subscription goes when an 11th device turns notifications on
B64URL = r"^[A-Za-z0-9_-]+=*$"


@router.get("/vapid-key")
async def vapid_key() -> dict:
    return {"key": settings.vapid_public_key}


class Keys(BaseModel):
    p256dh: str = Field(min_length=80, max_length=100, pattern=B64URL)  # the browser's P-256 public key (65 bytes)
    auth: str = Field(min_length=16, max_length=32, pattern=B64URL)  # its 16-byte auth secret


class SubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=2048)
    keys: Keys
    user_agent: str = Field(default="", max_length=300)


@router.post("/subscribe")
async def subscribe(body: SubscriptionIn, p: Principal = Depends(user_principal),
                    s: AsyncSession = Depends(own_db)) -> dict:
    await enforce(f"push-subscribe:{p.user_id}", 20, 3600)
    if not push_endpoint_ok(body.endpoint):
        raise HTTPException(422, "unsupported_push_service")
    # An endpoint belongs to one browser: if another account signed in there before, it moves to this one, so their
    # notifications stop going to this person's device (and the unique endpoint doesn't clash).
    async with system_session() as sys:
        await sys.execute(delete(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint, PushSubscription.user_id != p.user_id))
    existing = await s.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if existing:
        existing.p256dh, existing.auth = body.keys.p256dh, body.keys.auth
    else:
        s.add(PushSubscription(user_id=p.user_id, endpoint=body.endpoint, p256dh=body.keys.p256dh,
                               auth=body.keys.auth, user_agent=body.user_agent))
        await s.flush()
        if await s.scalar(select(func.count()).select_from(PushSubscription)) > MAX_DEVICES:
            oldest = await s.scalar(select(PushSubscription.id).order_by(PushSubscription.created_at).limit(1))
            await s.execute(delete(PushSubscription).where(PushSubscription.id == oldest))
    return {"ok": True}


class UnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=2048)


@router.post("/unsubscribe")
async def unsubscribe(body: UnsubscribeIn, s: AsyncSession = Depends(own_db)) -> dict:
    sub = await s.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub:
        await s.delete(sub)
    return {"ok": True}


@router.post("/test")
async def test(p: Principal = Depends(user_principal)) -> dict:
    await enforce(f"push-test:{p.user_id}", 5, 3600)
    await notify(p.user_id, "system", "Notifications are on ✅", "We'll nudge you about savings, deals and goals.")
    return {"ok": True}
