"""Passwords, JWT access tokens and server-side sessions with an idle lock.

Session model (all in Dragonfly):
  sess:{sid}         hash {user_id, role, refresh_hash, created}   TTL = refresh_token_days
  sess:{sid}:active  "1"                                           TTL = idle_lock_minutes

When `sess:{sid}:active` expires the session is *locked*: the API answers 423 until the
person unlocks with their password or a passkey (fingerprint / face), like banking apps.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.cache import redis
from app.core.config import settings
from app.core.crypto import sha256

_hasher = PasswordHasher()
ALGO = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerificationError:
        return False
    except Exception:
        return False


@dataclass
class SessionInfo:
    sid: str
    user_id: uuid.UUID
    role: str


def _sess_key(sid: str) -> str:
    return f"sess:{sid}"


def _active_key(sid: str) -> str:
    return f"sess:{sid}:active"


def create_access_token(user_id: uuid.UUID, role: str, sid: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "sid": sid,
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        return None
    return payload if payload.get("typ") == "access" else None


async def create_session(user_id: uuid.UUID, role: str) -> tuple[str, str]:
    """Returns (sid, refresh_token)."""
    sid = secrets.token_urlsafe(16)
    secret = secrets.token_urlsafe(32)
    ttl = settings.refresh_token_days * 86400
    await redis.hset(_sess_key(sid), mapping={
        "user_id": str(user_id), "role": role, "refresh_hash": sha256(secret),
        "created": datetime.now(UTC).isoformat(),
    })
    await redis.expire(_sess_key(sid), ttl)
    await redis.sadd(f"user_sessions:{user_id}", sid)
    await touch_session(sid)
    return sid, f"{sid}.{secret}"


async def touch_session(sid: str) -> None:
    await redis.set(_active_key(sid), "1", ex=settings.idle_lock_minutes * 60)


async def session_state(sid: str) -> str:
    """'active', 'locked' or 'missing'."""
    if not await redis.exists(_sess_key(sid)):
        return "missing"
    if not await redis.exists(_active_key(sid)):
        return "locked"
    return "active"


async def get_session(sid: str) -> SessionInfo | None:
    data = await redis.hgetall(_sess_key(sid))
    if not data:
        return None
    return SessionInfo(sid=sid, user_id=uuid.UUID(data["user_id"]), role=data["role"])


async def rotate_refresh(refresh_token: str) -> tuple[SessionInfo, str] | None:
    """Validate a refresh token and issue a new one for the same session."""
    try:
        sid, secret = refresh_token.split(".", 1)
    except ValueError:
        return None
    data = await redis.hgetall(_sess_key(sid))
    if not data or not secrets.compare_digest(data.get("refresh_hash", ""), sha256(secret)):
        return None
    new_secret = secrets.token_urlsafe(32)
    await redis.hset(_sess_key(sid), "refresh_hash", sha256(new_secret))
    return SessionInfo(sid=sid, user_id=uuid.UUID(data["user_id"]), role=data["role"]), f"{sid}.{new_secret}"


async def update_session_role(user_id: uuid.UUID, role: str) -> None:
    for sid in await redis.smembers(f"user_sessions:{user_id}"):
        if await redis.exists(_sess_key(sid)):
            await redis.hset(_sess_key(sid), "role", role)


async def revoke_session(sid: str) -> None:
    data = await redis.hgetall(_sess_key(sid))
    await redis.delete(_sess_key(sid), _active_key(sid))
    if data:
        await redis.srem(f"user_sessions:{data['user_id']}", sid)


async def revoke_all_sessions(user_id: uuid.UUID) -> None:
    for sid in await redis.smembers(f"user_sessions:{user_id}"):
        await redis.delete(_sess_key(sid), _active_key(sid))
    await redis.delete(f"user_sessions:{user_id}")
