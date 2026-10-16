import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import Principal, current_principal, own_db
from app.models import EmailConnection, IngestedEmail
from app.services import gmail

router = APIRouter(prefix="/email", tags=["email"])


@router.get("/connections")
async def connections(s: AsyncSession = Depends(own_db)) -> dict:
    rows = (await s.execute(select(EmailConnection).order_by(EmailConnection.created_at))).scalars().all()
    out = []
    for c in rows:
        found = await s.scalar(select(func.count()).select_from(IngestedEmail).where(
            IngestedEmail.connection_id == c.id, IngestedEmail.status == "transaction"))
        out.append({"id": str(c.id), "provider": c.provider, "email": c.email_address, "status": c.status,
                    "last_error": c.last_error, "last_synced_at": c.last_synced_at, "transactions_found": found})
    return {"configured": bool(settings.google_client_id), "connections": out}


@router.post("/google/start")
async def google_start(p: Principal = Depends(current_principal)) -> dict:
    if not settings.google_client_id:
        raise HTTPException(503, "gmail_not_configured")
    return {"url": gmail.auth_url(p.user_id)}


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None,
                          error: str | None = None) -> RedirectResponse:
    target = f"{settings.frontend_url}/dashboard?settings=email"
    if error or not code or not state:
        return RedirectResponse(f"{target}&error={error or 'cancelled'}")
    user_id = gmail.user_from_state(state)
    if not user_id:
        return RedirectResponse(f"{target}&error=expired")
    try:
        conn = await gmail.exchange_code(user_id, code)
    except Exception:
        return RedirectResponse(f"{target}&error=exchange_failed")
    asyncio.get_running_loop().create_task(gmail.sync_connection(conn.id, user_id))
    return RedirectResponse(f"{target}&connected=1")


@router.post("/connections/{conn_id}/sync")
async def sync_now(conn_id: uuid.UUID, p: Principal = Depends(current_principal)) -> dict:
    created = await gmail.sync_connection(conn_id, p.user_id)
    return {"ok": True, "new_transactions": created}


@router.delete("/connections/{conn_id}")
async def disconnect(conn_id: uuid.UUID, s: AsyncSession = Depends(own_db)) -> dict:
    conn = await s.get(EmailConnection, conn_id)
    if conn:
        await gmail.revoke(conn)
        await s.delete(conn)
    return {"ok": True}
