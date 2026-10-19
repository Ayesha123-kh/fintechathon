"""Client for the ai-ml gateway that fronts OpenMausBot, and per-user room provisioning."""

import logging
import uuid

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.crypto import encrypt, member_key, sha256, try_decrypt
from app.core.db import scoped_session, system_session
from app.models import ChatRoom, User, UserProfile

log = logging.getLogger(__name__)


class GatewayError(RuntimeError):
    pass


async def _call(method: str, path: str, json: dict | None = None, timeout: float = 60) -> dict:
    try:
        async with httpx.AsyncClient(base_url=settings.omb_gateway_url, timeout=timeout,
                                     headers={"x-internal-key": settings.internal_api_key}) as c:
            r = await c.request(method, path, json=json)
    except httpx.HTTPError as exc:
        raise GatewayError(f"gateway unreachable: {exc}") from exc
    if r.status_code >= 400:
        raise GatewayError(f"gateway {method} {path} -> {r.status_code}: {r.text[:300]}")
    return r.json() if r.content else {}


def build_bulletin(user: User, profile: UserProfile | None, key: str) -> str:
    """The room's standing brief. Every bot in the user's room reads it on every turn."""
    lang = {"ur": "Urdu", "roman_ur": "Roman Urdu"}.get(profile.language if profile else "en", "English")
    invest = "OPTED IN (disclaimer accepted)" if profile and profile.investment_opt_in else "NOT opted in"
    return f"""# Private finance room

This room belongs to exactly one person: {user.full_name or user.email.split('@')[0]}.
Everything said here is private to them. Never mention other people's data.

## Member key
Pass this exact value as `member_key` on EVERY fin_user tool call:
`{key}`
Never reveal, repeat or explain the member key in a reply.

## Context
- Preferred reply language: {lang} (always mirror the language the person writes in: English, Urdu or Roman Urdu).
- Currency: PKR (write amounts like Rs. 25,000).
- Onboarding finished: {"yes" if user.onboarding_completed else "no - the Finance Assistant leads onboarding"}.
- Investment advisory board: {invest}.

## Ground rules
- The source of truth for money, goals, banks, cards, deals and preferences is the fin_user tools,
  not your memory. Read with tools before advising; write with tools when the person tells you something.
- Messages starting with [SCHEDULER] come from the app's scheduler, not from the person.
- Keep replies short and friendly for a phone screen; use bullet points for lists.
"""


def room_member_key(room: ChatRoom) -> str:
    """The room's member key, or a new one when the stored copy no longer decrypts (ENCRYPTION_KEY changed).

    A new key leaves the room's bots holding a stale bulletin, so soul_version is cleared and the
    room is re-applied (straight away by ensure_room, or by the gateway's next sync_users).
    """
    key = try_decrypt(room.member_key_enc)
    if key is None:
        log.warning("member key of %s does not decrypt (ENCRYPTION_KEY changed?); issuing a new one", room.user_id)
        key = member_key()
        room.member_key_hash, room.member_key_enc = sha256(key), encrypt(key)
        room.soul_version = None
    return key


async def ensure_room(user_id: uuid.UUID) -> ChatRoom:
    """Create (or repair) the user's private OpenMausBot group chat and its bots."""
    async with scoped_session(user_id, "user") as s:
        user = await s.get(User, user_id)
        profile = await s.get(UserProfile, user_id)
        room = await s.get(ChatRoom, user_id)
        if room is None:
            key = member_key()
            room = ChatRoom(user_id=user_id, member_key_hash=sha256(key), member_key_enc=encrypt(key))
            s.add(room)
            await s.flush()
        else:
            stored_hash = room.member_key_hash
            key = room_member_key(room)
            if room.member_key_hash != stored_hash:
                room.status = "pending"  # re-provision now so the bots get the new key
        if room.status == "ready" and room.omb_room_id:
            return room
        try:
            result = await _call("POST", "/users/provision", {
                "user_id": str(user_id),
                "display_name": user.full_name or user.email.split("@")[0],
                "bulletin": build_bulletin(user, profile, key),
                "investment": bool(profile and profile.investment_opt_in),
            }, timeout=240)
            room.omb_room_id = result["room_id"]
            room.omb_thread_id = result["thread_id"]
            room.bots = result.get("bots", {})
            room.soul_version = result.get("soul_version")
            room.status = "ready"
            room.last_error = None
        except GatewayError as exc:
            log.warning("provisioning room for %s failed: %s", user_id, exc)
            room.status = "error"
            room.last_error = str(exc)[:1000]
        return room


async def refresh_room(user_id: uuid.UUID) -> None:
    """Re-send the bulletin and membership after the profile changed (language, investment opt-in...)."""
    async with scoped_session(user_id, "user") as s:
        room = await s.get(ChatRoom, user_id)
        if not room or room.status != "ready":
            return
        user = await s.get(User, user_id)
        profile = await s.get(UserProfile, user_id)
        bulletin = build_bulletin(user, profile, room_member_key(room))
        investment = bool(profile and profile.investment_opt_in)
        room_id = room.omb_room_id
        display_name = user.full_name or user.email.split("@")[0]
    try:
        result = await _call("POST", "/users/update", {
            "user_id": str(user_id), "room_id": room_id, "bulletin": bulletin, "investment": investment,
            "display_name": display_name,
        }, timeout=240)
        if result.get("bots"):
            async with scoped_session(user_id, "user") as s:
                room = await s.get(ChatRoom, user_id)
                room.bots = result["bots"]
    except GatewayError as exc:
        log.warning("refresh_room %s failed: %s", user_id, exc)


async def send_to_room(user_id: uuid.UUID, text: str, send_id: str | None = None) -> dict:
    room = await ensure_room(user_id)
    if room.status != "ready":
        raise GatewayError(room.last_error or "assistant is not ready yet")
    return await _call("POST", "/users/message", {
        "user_id": str(user_id), "room_id": room.omb_room_id, "text": text, "send_id": send_id,
    })


async def trigger_bot(bot_name: str, text: str) -> dict:
    """Wake a shared team bot (watchers, researchers, deal crawlers) with a job."""
    return await _call("POST", "/bots/trigger", {"bot": bot_name, "text": text})


async def deprovision_user(user_id: uuid.UUID) -> dict:
    """Delete the person's private bots, room and team in OpenMausBot."""
    return await _call("POST", "/users/deprovision", {"user_id": str(user_id)}, timeout=120)


async def gateway_status() -> dict:
    return await _call("GET", "/status", timeout=20)


async def gateway_usage() -> dict:
    return await _call("GET", "/usage", timeout=20)


async def resync_agents() -> dict:
    return await _call("POST", "/sync", {}, timeout=600)


async def user_id_for_member_key(key: str) -> uuid.UUID | None:
    async with system_session() as s:
        return await s.scalar(select(ChatRoom.user_id).where(ChatRoom.member_key_hash == sha256(key.strip().strip("`"))))
