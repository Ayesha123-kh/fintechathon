import asyncio
import json
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.cache import rate_limit, redis
from app.core.config import settings
from app.core.crypto import sha256
from app.core.db import scoped_session, system_session
from app.core.deps import ACCESS_COOKIE, REFRESH_COOKIE, Principal, current_principal
from app.core.mailer import reset_email, send_email
from app.core.security import (
    create_access_token,
    create_session,
    get_session,
    hash_password,
    revoke_all_sessions,
    revoke_session,
    rotate_refresh,
    session_state,
    touch_session,
    verify_password,
)
from app.models import Plan, Subscription, User, UserProfile, WebAuthnCredential
from app.services.omb import ensure_room

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


class SigninIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class UnlockIn(BaseModel):
    password: str


def _client_ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0]


def _set_cookies(response: Response, access: str, refresh: str | None) -> None:
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "lax"}
    response.set_cookie(ACCESS_COOKIE, access, max_age=settings.access_token_minutes * 60, path="/", **common)
    if refresh:
        response.set_cookie(REFRESH_COOKIE, refresh, max_age=settings.refresh_token_days * 86400, path="/api/auth",
                            **common)


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


def user_out(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role,
            "onboarding_completed": user.onboarding_completed}


async def _login(response: Response, user: User) -> dict:
    sid, refresh = await create_session(user.id, user.role)
    _set_cookies(response, create_access_token(user.id, user.role, sid), refresh)
    return {"user": user_out(user)}


@router.post("/signup")
async def signup(body: SignupIn, request: Request, response: Response) -> dict:
    if not await rate_limit(f"signup:{_client_ip(request)}", 10, 3600):
        raise HTTPException(429, "too_many_attempts")
    email = body.email.lower()
    async with system_session() as s:
        if await s.scalar(select(User.id).where(User.email == email)):
            raise HTTPException(409, "email_taken")
        user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name.strip(),
                    last_login_at=datetime.now(UTC))
        s.add(user)
        await s.flush()
        s.add(UserProfile(user_id=user.id))
        free = await s.scalar(select(Plan).where(Plan.code == "free"))
        if free:
            s.add(Subscription(user_id=user.id, plan_id=free.id, status="active"))
    # Provision the private assistant chat in the background; the widget shows "setting up" meanwhile.
    asyncio.get_running_loop().create_task(ensure_room(user.id))
    return await _login(response, user)


@router.post("/signin")
async def signin(body: SigninIn, request: Request, response: Response) -> dict:
    email = body.email.lower()
    if not await rate_limit(f"signin:{_client_ip(request)}:{email}", 8, 900):
        raise HTTPException(429, "too_many_attempts")
    async with system_session() as s:
        user = await s.scalar(select(User).where(User.email == email))
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "invalid_credentials")
        if not user.is_active:
            raise HTTPException(403, "account_disabled")
        user.last_login_at = datetime.now(UTC)
    asyncio.get_running_loop().create_task(ensure_room(user.id))
    return await _login(response, user)


@router.post("/refresh")
async def refresh(request: Request, response: Response) -> dict:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(401, "no_session")
    sid = token.split(".", 1)[0]
    state = await session_state(sid)
    if state == "missing":
        _clear_cookies(response)
        raise HTTPException(401, "session_ended")
    if state == "locked":
        raise HTTPException(status.HTTP_423_LOCKED, "locked")
    rotated = await rotate_refresh(token)
    if not rotated:
        _clear_cookies(response)
        raise HTTPException(401, "session_ended")
    info, new_refresh = rotated
    _set_cookies(response, create_access_token(info.user_id, info.role, info.sid), new_refresh)
    return {"ok": True}


@router.get("/session")
async def session(request: Request) -> dict:
    """Lets the app decide between sign-in, lock screen and the dashboard on launch."""
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        return {"state": "none"}
    sid = token.split(".", 1)[0]
    state = await session_state(sid)
    if state == "missing":
        return {"state": "none"}
    info = await get_session(sid)
    async with scoped_session(info.user_id, "user") as s:
        user = await s.get(User, info.user_id)
        has_passkey = bool(await s.scalar(select(WebAuthnCredential.id).limit(1)))
    if not user or not user.is_active:
        return {"state": "none"}
    return {"state": state, "user": user_out(user), "has_passkey": has_passkey,
            "idle_lock_minutes": settings.idle_lock_minutes}


@router.post("/signout")
async def signout(request: Request, response: Response) -> dict:
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        await revoke_session(token.split(".", 1)[0])
    _clear_cookies(response)
    return {"ok": True}


@router.post("/forgot")
async def forgot(body: ForgotIn, request: Request) -> dict:
    if not await rate_limit(f"forgot:{_client_ip(request)}", 5, 3600):
        raise HTTPException(429, "too_many_attempts")
    email = body.email.lower()
    async with system_session() as s:
        user = await s.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user:
        token = secrets.token_urlsafe(32)
        await redis.set(f"pwreset:{sha256(token)}", str(user.id), ex=1800)
        link = f"{settings.frontend_url}/forgot-password?token={token}"
        text, html = reset_email(user.full_name, link)
        asyncio.get_running_loop().create_task(send_email(user.email, f"Reset your {settings.app_name} password", text, html))
    # Same answer either way so the endpoint cannot be used to discover accounts.
    return {"ok": True}


@router.post("/reset")
async def reset(body: ResetIn) -> dict:
    key = f"pwreset:{sha256(body.token)}"
    uid = await redis.getdel(key)
    if not uid:
        raise HTTPException(400, "invalid_or_expired_token")
    async with system_session() as s:
        user = await s.get(User, uuid.UUID(uid))
        user.password_hash = hash_password(body.password)
    await revoke_all_sessions(user.id)
    return {"ok": True}


@router.post("/unlock")
async def unlock(body: UnlockIn, request: Request, response: Response) -> dict:
    """Unlock an idle-locked session with the password."""
    token = request.cookies.get(REFRESH_COOKIE)
    info = await get_session(token.split(".", 1)[0]) if token else None
    if not info:
        raise HTTPException(401, "session_ended")
    if not await rate_limit(f"unlock:{info.sid}", 5, 900):
        await revoke_session(info.sid)
        _clear_cookies(response)
        raise HTTPException(401, "session_ended")
    async with system_session() as s:
        user = await s.get(User, info.user_id)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid_credentials")
    await touch_session(info.sid)
    _set_cookies(response, create_access_token(info.user_id, info.role, info.sid), None)
    return {"user": user_out(user)}


# ----------------------------------------------------------------- passkeys (fingerprint / face)

def _origins() -> list[str]:
    return list({settings.frontend_url.rstrip("/"), *[o.rstrip("/") for o in settings.cors_origins]})


@router.post("/webauthn/register/options")
async def passkey_register_options(p: Principal = Depends(current_principal)) -> Response:
    async with scoped_session(p.user_id, "user") as s:
        user = await s.get(User, p.user_id)
        existing = (await s.execute(select(WebAuthnCredential.credential_id))).scalars().all()
    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id, rp_name=settings.webauthn_rp_name, user_name=user.email,
        user_id=user.id.bytes, user_display_name=user.full_name or user.email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED, user_verification=UserVerificationRequirement.REQUIRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c)) for c in existing],
    )
    await redis.set(f"wa:reg:{p.user_id}", bytes_to_base64url(options.challenge), ex=300)
    return Response(options_to_json(options), media_type="application/json")


class PasskeyVerifyIn(BaseModel):
    credential: dict
    device_name: str = "This device"


@router.post("/webauthn/register/verify")
async def passkey_register_verify(body: PasskeyVerifyIn, p: Principal = Depends(current_principal)) -> dict:
    challenge = await redis.getdel(f"wa:reg:{p.user_id}")
    if not challenge:
        raise HTTPException(400, "challenge_expired")
    try:
        verified = verify_registration_response(
            credential=body.credential, expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=settings.webauthn_rp_id, expected_origin=_origins(), require_user_verification=True,
        )
    except Exception as exc:
        raise HTTPException(400, f"passkey_invalid: {exc}") from exc
    async with scoped_session(p.user_id, "user") as s:
        s.add(WebAuthnCredential(
            user_id=p.user_id, credential_id=bytes_to_base64url(verified.credential_id),
            public_key=verified.credential_public_key, sign_count=verified.sign_count,
            transports=body.credential.get("response", {}).get("transports", []), device_name=body.device_name[:120],
        ))
    return {"ok": True}


class PasskeyLoginOptionsIn(BaseModel):
    email: EmailStr | None = None
    purpose: str = "login"  # login | unlock


@router.post("/webauthn/options")
async def passkey_auth_options(body: PasskeyLoginOptionsIn, request: Request) -> Response:
    allow: list[PublicKeyCredentialDescriptor] = []
    user_id = None
    if body.purpose == "unlock":
        token = request.cookies.get(REFRESH_COOKIE)
        info = await get_session(token.split(".", 1)[0]) if token else None
        if not info:
            raise HTTPException(401, "session_ended")
        user_id = info.user_id
    elif body.email:
        async with system_session() as s:
            user_id = await s.scalar(select(User.id).where(User.email == body.email.lower()))
    if user_id:
        async with scoped_session(user_id, "user") as s:
            allow = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(c)) for c in
                     (await s.execute(select(WebAuthnCredential.credential_id))).scalars()]
    options = generate_authentication_options(rp_id=settings.webauthn_rp_id, allow_credentials=allow or None,
                                              user_verification=UserVerificationRequirement.REQUIRED)
    challenge = bytes_to_base64url(options.challenge)
    await redis.set(f"wa:auth:{challenge}", json.dumps({"purpose": body.purpose}), ex=300)
    return Response(options_to_json(options), media_type="application/json")


class PasskeyAuthIn(BaseModel):
    credential: dict
    challenge: str


@router.post("/webauthn/verify")
async def passkey_auth_verify(body: PasskeyAuthIn, request: Request, response: Response) -> dict:
    meta = await redis.getdel(f"wa:auth:{body.challenge}")
    if not meta:
        raise HTTPException(400, "challenge_expired")
    purpose = json.loads(meta)["purpose"]
    cred_id = body.credential.get("id") or body.credential.get("rawId")
    async with system_session() as s:
        cred = await s.scalar(select(WebAuthnCredential).where(WebAuthnCredential.credential_id == cred_id))
        if not cred:
            raise HTTPException(401, "unknown_passkey")
        try:
            verified = verify_authentication_response(
                credential=body.credential, expected_challenge=base64url_to_bytes(body.challenge),
                expected_rp_id=settings.webauthn_rp_id, expected_origin=_origins(),
                credential_public_key=cred.public_key, credential_current_sign_count=cred.sign_count,
                require_user_verification=True,
            )
        except Exception as exc:
            raise HTTPException(401, f"passkey_invalid: {exc}") from exc
        cred.sign_count = verified.new_sign_count
        cred.last_used_at = datetime.now(UTC)
        user = await s.get(User, cred.user_id)
        if not user.is_active:
            raise HTTPException(403, "account_disabled")
        user.last_login_at = datetime.now(UTC)
    if purpose == "unlock":
        token = request.cookies.get(REFRESH_COOKIE)
        info = await get_session(token.split(".", 1)[0]) if token else None
        if not info or info.user_id != user.id:
            raise HTTPException(401, "session_ended")
        await touch_session(info.sid)
        _set_cookies(response, create_access_token(info.user_id, info.role, info.sid), None)
        return {"user": user_out(user)}
    return await _login(response, user)


@router.get("/webauthn/credentials")
async def passkey_list(p: Principal = Depends(current_principal)) -> list[dict]:
    async with scoped_session(p.user_id, "user") as s:
        rows = (await s.execute(select(WebAuthnCredential).order_by(WebAuthnCredential.created_at))).scalars()
        return [{"id": str(c.id), "device_name": c.device_name, "created_at": c.created_at,
                 "last_used_at": c.last_used_at} for c in rows]


@router.delete("/webauthn/credentials/{cred_id}")
async def passkey_delete(cred_id: str, p: Principal = Depends(current_principal)) -> dict:
    async with scoped_session(p.user_id, "user") as s:
        cred = await s.get(WebAuthnCredential, uuid.UUID(cred_id))
        if cred:
            await s.delete(cred)
    return {"ok": True}
