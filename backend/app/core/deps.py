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


async def user_db(p: Principal = Depends(current_principal)) -> AsyncIterator[AsyncSession]:
    """Session where RLS limits every query to the caller's rows (admins see all)."""
    async with scoped_session(p.user_id, "admin" if p.is_admin else "user") as session:
        yield session


async def own_db(p: Principal = Depends(current_principal)) -> AsyncIterator[AsyncSession]:
    """Session limited to the caller's own rows even for admins (personal screens)."""
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
