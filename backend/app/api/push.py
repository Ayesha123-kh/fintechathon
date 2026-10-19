from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import Principal, own_db, user_principal
from app.models import PushSubscription
from app.services.notify import notify

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-key")
async def vapid_key() -> dict:
    return {"key": settings.vapid_public_key}


class Keys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: Keys
    user_agent: str = ""


@router.post("/subscribe")
async def subscribe(body: SubscriptionIn, p: Principal = Depends(user_principal),
                    s: AsyncSession = Depends(own_db)) -> dict:
    existing = await s.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if existing:
        existing.p256dh, existing.auth = body.keys.p256dh, body.keys.auth
    else:
        s.add(PushSubscription(user_id=p.user_id, endpoint=body.endpoint, p256dh=body.keys.p256dh,
                               auth=body.keys.auth, user_agent=body.user_agent[:300]))
    return {"ok": True}


class UnsubscribeIn(BaseModel):
    endpoint: str


@router.post("/unsubscribe")
async def unsubscribe(body: UnsubscribeIn, s: AsyncSession = Depends(own_db)) -> dict:
    sub = await s.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub:
        await s.delete(sub)
    return {"ok": True}


@router.post("/test")
async def test(p: Principal = Depends(user_principal)) -> dict:
    await notify(p.user_id, "system", "Notifications are on ✅", "We'll nudge you about savings, deals and goals.")
    return {"ok": True}
