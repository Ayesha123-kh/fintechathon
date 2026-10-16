"""Testing helpers, available only outside production."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import rate_limit
from app.core.deps import Principal, current_principal
from app.services.test_alerts import TestAlertError, send_test_alert

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/test-alert")
async def test_alert(p: Principal = Depends(current_principal)) -> dict:
    if not await rate_limit(f"testalert:{p.user_id}", 10, 60):
        raise HTTPException(429, "slow_down")
    try:
        return await send_test_alert(p.user_id)
    except TestAlertError as exc:
        status = 404 if str(exc) == "test_tools_disabled" else 503 if str(exc) in ("smtp_not_configured", "send_failed") else 400
        raise HTTPException(status, str(exc)) from exc
