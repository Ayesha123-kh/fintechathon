import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

log = logging.getLogger(__name__)


async def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    if not settings.smtp_username or not settings.smtp_password:
        log.warning("SMTP not configured; email to %s not sent. Subject=%s\n%s", to, subject, text)
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_username
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,  # Gmail: an App Password, not the account password
            start_tls=True,
        )
        return True
    except Exception:
        log.exception("failed to send email to %s", to)
        return False


def reset_email(name: str, link: str) -> tuple[str, str]:
    text = (
        f"Assalam o Alaikum {name or ''},\n\nWe received a request to reset your {settings.app_name} password.\n"
        f"Open this link within 30 minutes to choose a new one:\n{link}\n\n"
        "If you didn't ask for this, you can ignore this email."
    )
    html = f"""
    <div style="font-family:system-ui,sans-serif;background:#EAFFD0;padding:24px">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:20px;padding:28px">
        <h2 style="color:#224F10;margin-top:0">Reset your password</h2>
        <p style="color:#0D0D0D">Assalam o Alaikum {name or ''}, tap the button within 30 minutes to choose a new
        password.</p>
        <a href="{link}" style="display:inline-block;background:#B0E454;color:#0D0D0D;padding:12px 22px;
        border-radius:999px;text-decoration:none;font-weight:600">Choose a new password</a>
        <p style="color:#555;font-size:13px">If you didn't ask for this, ignore this email.</p>
      </div>
    </div>"""
    return text, html
