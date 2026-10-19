import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import limits
from app.core.cache import chat_channel, presence_key, rate_limit, redis
from app.core.db import scoped_session
from app.core.deps import Principal, own_db, passive_user_principal, user_principal
from app.core.llm import transcribe
from app.models import ChatMessage, ChatRoom, Notification, UserProfile
from app.services.gmail import must_connect_first
from app.services.omb import GatewayError, ensure_room, send_to_room
from app.services.voice import BadAudio, wav_info

router = APIRouter(prefix="/chat", tags=["chat"])


def message_out(m: ChatMessage) -> dict:
    return {"id": str(m.id), "role": m.role, "sender": m.sender, "text": m.text, "kind": m.kind,
            "final": m.final, "created_at": m.created_at.isoformat() if m.created_at else None}


@router.get("/status")
async def status(p: Principal = Depends(user_principal)) -> dict:
    room = await ensure_room(p.user_id)
    return {"status": room.status, "advisors": [v.get("label", k) for k, v in (room.bots or {}).items()]}


@router.get("/unread")
async def unread(p: Principal = Depends(user_principal), s: AsyncSession = Depends(own_db)) -> dict:
    """Bot replies and notifications that arrived since the person last opened the chat."""
    profile = await s.get(UserProfile, p.user_id)
    read_at = profile.chat_read_at if profile else None
    stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.role == "bot", ChatMessage.final.is_(True))
    if read_at:
        stmt = stmt.where(ChatMessage.created_at > read_at)
    return {"count": await s.scalar(stmt), "read_at": read_at.isoformat() if read_at else None}


@router.post("/read")
async def mark_read(p: Principal = Depends(user_principal), s: AsyncSession = Depends(own_db)) -> dict:
    profile = await s.get(UserProfile, p.user_id)
    if profile:
        profile.chat_read_at = datetime.now(UTC)
    await s.execute(update(Notification).where(Notification.read_at.is_(None)).values(read_at=datetime.now(UTC)))
    return {"ok": True}


@router.get("/messages")
async def history(before: datetime | None = None, limit: int = 40, s: AsyncSession = Depends(own_db)) -> list[dict]:
    stmt = select(ChatMessage)
    if before:
        stmt = stmt.where(ChatMessage.created_at < before)
    rows = (await s.execute(stmt.order_by(ChatMessage.created_at.desc()).limit(min(limit, 100)))).scalars().all()
    return [message_out(m) for m in reversed(rows)]


class SendIn(BaseModel):
    text: str = Field(min_length=1, max_length=limits.CHAT_TEXT_MAX)


async def _send(user_id: uuid.UUID, text: str) -> dict:
    if not await rate_limit(f"chat:{user_id}", 30, 60):
        raise HTTPException(429, "slow_down")
    send_id = uuid.uuid4().hex
    async with scoped_session(user_id, "user") as s:
        if await must_connect_first(s, user_id):
            raise HTTPException(409, "connect_gmail_first")
        msg = ChatMessage(user_id=user_id, role="user", sender="you", text=text, omb_message_id=None)
        s.add(msg)
        await s.flush()
        out = message_out(msg)
    await redis.publish(chat_channel(str(user_id)), json.dumps({"type": "message", "message": out}))
    try:
        await send_to_room(user_id, text, send_id)
    except GatewayError as exc:
        raise HTTPException(503, f"assistant_unavailable: {exc}") from exc
    return out


@router.post("/messages")
async def send(body: SendIn, p: Principal = Depends(user_principal)) -> dict:
    return await _send(p.user_id, body.text.strip())


@router.post("/transcribe")
async def transcribe_voice(audio: UploadFile = File(...), p: Principal = Depends(user_principal)) -> dict:
    """Speech to text only: the app puts the text in the message box for the person to edit and send."""
    data = await audio.read(limits.VOICE_MAX_BYTES + 1)
    if len(data) > limits.VOICE_MAX_BYTES:
        raise HTTPException(413, "audio_too_long")
    try:
        seconds = wav_info(data).seconds
    except BadAudio as exc:
        raise HTTPException(415, "audio_must_be_wav") from exc
    if seconds > limits.VOICE_MAX_SECONDS + 0.5:  # the app stops recording at 30 s
        raise HTTPException(413, "audio_too_long")
    if seconds < limits.VOICE_MIN_SECONDS:
        raise HTTPException(422, "audio_too_short")
    async with scoped_session(p.user_id, "user") as s:
        profile = await s.get(UserProfile, p.user_id)
    try:
        text = await transcribe(data, urdu_script=bool(profile and profile.language == "ur"))
    except Exception as exc:
        raise HTTPException(503, f"speech_to_text_unavailable: {exc}") from exc
    if not text:
        raise HTTPException(422, "could_not_understand_audio")
    return {"text": text}


@router.get("/stream")
async def stream(p: Principal = Depends(passive_user_principal)) -> StreamingResponse:
    """Server-sent events with new / updated chat messages. Also marks the user as online,
    so replies are not duplicated as push notifications while the app is open."""
    user_id = str(p.user_id)

    async def events():
        pubsub = redis.pubsub()
        await pubsub.subscribe(chat_channel(user_id))
        try:
            yield "retry: 3000\n\n"
            ticks = 0
            while True:
                if ticks % 15 == 0:
                    await redis.set(presence_key(user_id), "1", ex=40)
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    yield f"data: {msg['data']}\n\n"
                ticks += 1
                if ticks % 20 == 0:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(chat_channel(user_id))
            await pubsub.aclose()
            await redis.delete(presence_key(user_id))

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


@router.post("/reset-room")
async def reset_room(p: Principal = Depends(user_principal)) -> dict:
    """Retry provisioning after an error."""
    async with scoped_session(p.user_id, "user") as s:
        room = await s.get(ChatRoom, p.user_id)
        if room and room.status == "error":
            room.status = "pending"
    room = await ensure_room(p.user_id)
    return {"status": room.status}
