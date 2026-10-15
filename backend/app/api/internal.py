"""Endpoints only the ai-ml gateway calls (shared secret in `x-internal-key`)."""

import json
import logging
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.cache import chat_channel, redis
from app.core.crypto import decrypt
from app.core.db import scoped_session, system_session
from app.core.deps import require_internal
from app.models import AgentRegistry, ChatMessage, ChatRoom, User, UserProfile, WatchCluster
from app.services.notify import notify
from app.services.omb import build_bulletin

log = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)])


class OmbMessage(BaseModel):
    id: str
    role: str
    kind: str = "text"
    text: str = ""
    sender: str = ""
    final: bool = False


class OmbEvent(BaseModel):
    thread_id: str
    message: OmbMessage


_KEY_LEAK = re.compile(r"\b(?:[a-z]+-){4}\d{2}(?:-[a-z]+){3}\b")


@router.post("/omb/events")
async def omb_events(events: list[OmbEvent]) -> dict:
    """Bot replies in users' rooms, relayed from the OpenMausBot event stream."""
    handled = 0
    for ev in events:
        if ev.message.role != "bot" or ev.message.kind != "text" or not ev.message.text.strip():
            continue
        async with system_session() as s:
            user_id = await s.scalar(select(ChatRoom.user_id).where(ChatRoom.omb_thread_id == ev.thread_id))
        if not user_id:
            continue
        # Defence in depth: never show the member key even if a bot repeats it.
        text = _KEY_LEAK.sub("•••", ev.message.text)
        async with scoped_session(user_id, "user") as s:
            stmt = insert(ChatMessage).values(
                user_id=user_id, omb_message_id=ev.message.id, role="bot", sender=ev.message.sender[:80],
                text=text, kind="text", final=ev.message.final,
            ).on_conflict_do_update(
                index_elements=["omb_message_id"],
                set_={"text": text, "final": ev.message.final, "sender": ev.message.sender[:80]},
            ).returning(ChatMessage.id, ChatMessage.created_at)
            row = (await s.execute(stmt)).one()
        payload = {"type": "message", "message": {
            "id": str(row.id), "role": "bot", "sender": ev.message.sender, "text": text, "kind": "text",
            "final": ev.message.final, "created_at": row.created_at.isoformat(),
        }}
        await redis.publish(chat_channel(str(user_id)), json.dumps(payload))
        if ev.message.final:
            snippet = text if len(text) <= 160 else text[:157] + "…"
            await notify(user_id, "chat", ev.message.sender or "Your assistant", snippet, url="/dashboard?chat=1",
                         only_if_offline=True)
        handled += 1
    return {"handled": handled}


@router.get("/agents/users")
async def agent_users() -> list[dict]:
    """Every provisioned room, so the gateway can re-apply bots when SOUL files change."""
    async with system_session() as s:
        rows = (await s.execute(
            select(ChatRoom, User, UserProfile).join(User, User.id == ChatRoom.user_id)
            .outerjoin(UserProfile, UserProfile.user_id == ChatRoom.user_id)
            .where(ChatRoom.status == "ready", User.is_active.is_(True))
        )).all()
        return [{
            "user_id": str(room.user_id), "room_id": room.omb_room_id, "soul_version": room.soul_version,
            "display_name": user.full_name or user.email.split("@")[0],
            "investment": bool(profile and profile.investment_opt_in),
            "bulletin": build_bulletin(user, profile, decrypt(room.member_key_enc)),
        } for room, user, profile in rows]


class SoulVersionIn(BaseModel):
    user_id: str
    soul_version: str
    bots: dict


@router.post("/agents/users/soul-version")
async def set_soul_version(body: SoulVersionIn) -> dict:
    async with system_session() as s:
        room = await s.scalar(select(ChatRoom).where(ChatRoom.user_id == body.user_id))
        if room:
            room.soul_version = body.soul_version
            room.bots = body.bots
    return {"ok": True}


@router.get("/clusters")
async def clusters() -> list[dict]:
    async with system_session() as s:
        rows = (await s.execute(select(WatchCluster).where(WatchCluster.active.is_(True)))).scalars()
        return [{"slug": c.slug, "asset_class": c.asset_class, "name": c.name, "description": c.description,
                 "symbols": c.symbols} for c in rows]


class RegistryRow(BaseModel):
    name: str
    team: str
    kind: str
    soul_hash: str | None = None
    omb_bot_id: str | None = None
    status: str = "ok"
    last_error: str | None = None


@router.post("/agents/registry")
async def registry(rows: list[RegistryRow]) -> dict:
    async with system_session() as s:
        for r in rows:
            values = r.model_dump()
            await s.execute(insert(AgentRegistry).values(**values).on_conflict_do_update(
                index_elements=["name"], set_={k: v for k, v in values.items() if k != "name"}))
    return {"ok": True}
