from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import scoped_session
from app.core.security import decode_access_token, session_state, touch_session

ACCESS_COOKIE = "at"
REFRESH_COOKIE = "rt"


@dataclass
class Principal:
    user_id: UUID
    role: str
    sid: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def client_ip(request: Request) -> str:
    """The caller's IP address for rate limits, taken from the right of X-Forwarded-For (see trusted_proxy_hops).
    Never the left-most entry: a client can send its own X-Forwarded-For, and proxies append to it."""
    forwarded = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    hops = settings.trusted_proxy_hops
    if hops > 0 and len(forwarded) >= hops:
        return forwarded[-hops]
    return request.client.host if request.client else ""


def _token_from(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return request.cookies.get(ACCESS_COOKIE)


async def _principal(request: Request, touch: bool) -> Principal:
    token = _token_from(request)
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    sid = payload["sid"]
    state = await session_state(sid)
    if state == "missing":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session_ended")
    if state == "locked":
        raise HTTPException(status.HTTP_423_LOCKED, "locked")
    if touch:
        await touch_session(sid)
    return Principal(user_id=UUID(payload["sub"]), role=payload["role"], sid=sid)


async def current_principal(request: Request) -> Principal:
    """Authenticated user; counts as activity for the idle lock."""
    return await _principal(request, touch=True)


async def passive_principal(request: Request) -> Principal:
    """Authenticated user for background connections (SSE) that must not keep the session awake."""
    return await _principal(request, touch=False)


async def require_admin(p: Principal = Depends(current_principal)) -> Principal:
    if not p.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return p


def _reject_admin(p: Principal) -> Principal:
    # Admin accounts only run the admin dashboard; they have no finances, goals or assistant chat.
    if p.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_account")
    return p


async def user_principal(p: Principal = Depends(current_principal)) -> Principal:
    """Authenticated regular user; admin accounts are refused."""
    return _reject_admin(p)


async def passive_user_principal(p: Principal = Depends(passive_principal)) -> Principal:
    """Like passive_principal, for regular users only."""
    return _reject_admin(p)


async def own_db(p: Principal = Depends(user_principal)) -> AsyncIterator[AsyncSession]:
    """Session limited to the caller's own rows (regular users only)."""
    async with scoped_session(p.user_id, "user") as session:
        yield session


async def admin_db(p: Principal = Depends(require_admin)) -> AsyncIterator[AsyncSession]:
    async with scoped_session(p.user_id, "admin") as session:
        yield session


async def require_internal(x_internal_key: str = Header(default="")) -> None:
    """Calls from the OpenMausBot gateway."""
    import secrets

    if not secrets.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad_internal_key")
