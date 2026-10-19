"""Testing helpers, available only outside production."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import enforce
from app.core.deps import Principal, user_principal
from app.services.test_alerts import TestAlertError, send_test_alert

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/test-alert")
async def test_alert(p: Principal = Depends(user_principal)) -> dict:
    await enforce(f"testalert:{p.user_id}", 10, 60, "slow_down")
    await enforce(f"testalert-day:{p.user_id}", 50, 86400)  # each one is an email sent from our SMTP account
    try:
        return await send_test_alert(p.user_id)
    except TestAlertError as exc:
        status = 404 if str(exc) == "test_tools_disabled" else 503 if str(exc) in ("smtp_not_configured", "send_failed") else 400
        raise HTTPException(status, str(exc)) from exc
