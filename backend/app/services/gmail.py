"""Gmail (read-only) connection and bank-alert ingestion.

Only messages from the alert domains of banks the user told us about are fetched.
Each one is parsed into a transaction (regex fast path, LLM fallback) exactly once.
"""

import base64
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

import httpx
import jwt
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.core.config import settings
from app.core.crypto import encrypt, try_decrypt
from app.core.db import scoped_session, system_session
from app.core.llm import complete_json
from app.models import Bank, BankAccount, Card, EmailConnection, IngestedEmail, User
from app.services import finance
from app.services.notify import notify
from app.services.text import transaction_kind

log = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPES = "https://www.googleapis.com/auth/gmail.readonly openid email"
TEST_ALERT_SUBJECT = "Saving test alert"


async def must_connect_first(s, user_id: uuid.UUID) -> bool:
    """Onboarding starts only once an inbox is connected, so the assistant can see real spending from the start.
    Skipped when Gmail isn't configured on this server, so the app still works without it."""
    if not settings.google_client_id:
        return False
    user = await s.get(User, user_id)
    if not user or user.onboarding_completed:
        return False
    return not await s.scalar(select(EmailConnection.id).where(
        EmailConnection.user_id == user_id, EmailConnection.status != "revoked").limit(1))


def redirect_uri() -> str:
    return f"{settings.public_api_url}/email/google/callback"


def auth_url(user_id: uuid.UUID) -> str:
    state = jwt.encode({"uid": str(user_id), "exp": datetime.now(UTC) + timedelta(minutes=10), "p": "gmail"},
                       settings.jwt_secret, algorithm="HS256")
    return AUTH_URL + "?" + urlencode({
        "client_id": settings.google_client_id, "redirect_uri": redirect_uri(), "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true",
        "state": state,
    })


def user_from_state(state: str) -> uuid.UUID | None:
    try:
        data = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return uuid.UUID(data["uid"]) if data.get("p") == "gmail" else None


async def exchange_code(user_id: uuid.UUID, code: str) -> EmailConnection:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(TOKEN_URL, data={
            "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri(), "grant_type": "authorization_code",
        })
        r.raise_for_status()
        tok = r.json()
        profile = await c.get(f"{GMAIL}/profile", headers={"Authorization": f"Bearer {tok['access_token']}"})
        profile.raise_for_status()
        address = profile.json()["emailAddress"]
    async with scoped_session(user_id, "user") as s:
        conn = await s.scalar(select(EmailConnection).where(EmailConnection.email_address == address))
        if not conn:
            conn = EmailConnection(user_id=user_id, email_address=address, access_token_enc="",
                                   sync_from=(datetime.now(UTC) - timedelta(days=30)).date())
            s.add(conn)
        conn.access_token_enc = encrypt(tok["access_token"])
        if tok.get("refresh_token"):
            conn.refresh_token_enc = encrypt(tok["refresh_token"])
        conn.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(tok.get("expires_in", 3600)) - 60)
        conn.status, conn.last_error = "active", None
        await s.flush()
        return conn


async def _access_token(conn: EmailConnection) -> str:
    if conn.token_expires_at and conn.token_expires_at > datetime.now(UTC):
        if (token := try_decrypt(conn.access_token_enc)) is not None:
            return token
    if not conn.refresh_token_enc:
        raise RuntimeError("no refresh token; reconnect Gmail")
    refresh_token = try_decrypt(conn.refresh_token_enc)
    if refresh_token is None:
        raise PermissionError("stored Gmail tokens no longer decrypt (ENCRYPTION_KEY changed); reconnect Gmail")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(TOKEN_URL, data={
            "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        })
    if r.status_code in (400, 401):
        raise PermissionError("Gmail access was revoked; reconnect Gmail")
    r.raise_for_status()
    tok = r.json()
    conn.access_token_enc = encrypt(tok["access_token"])
    conn.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(tok.get("expires_in", 3600)) - 60)
    return tok["access_token"]


async def revoke(conn: EmailConnection) -> None:
    token = try_decrypt(conn.refresh_token_enc or conn.access_token_enc)
    if token is None:  # encrypted under an old key; nothing we can revoke
        return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post("https://oauth2.googleapis.com/revoke", params={"token": token})
    except httpx.HTTPError:
        pass


# ---------------------------------------------------------------- parsing

AMOUNT = r"(?:PKR|Rs\.?|RS\.?)\s?([\d,]+(?:\.\d{1,2})?)"
_DEBIT = re.compile(r"\b(debited|spent|subscribed|topped up|withdrawn|withdrawal|purchase|paid|payment of|charged|sent|transferred to)\b", re.IGNORECASE)
_CREDIT = re.compile(r"\b(credited|received|got|deposited|refund(?:ed)?|salary|transferred from|cash ?back)\b", re.IGNORECASE)
_AMOUNT = re.compile(AMOUNT, re.IGNORECASE)
_BAL = re.compile(r"(?:avail\w*|available|current|remaining)\s*(?:bal\w*|limit)[^\d]{0,20}?" + AMOUNT, re.IGNORECASE)
# Bank boilerplate that the "at / to ..." pattern can catch ("contact us at 111-331-331").
_NOT_A_NAME = re.compile(r"\b(?:rs|pkr|us|please|contact|inform|visit|website|customer|inquiry)\b", re.IGNORECASE)
# Meezan-style details block: "Beneficiary Account Title: : M.FAHEEM Branch : ..."
_BENEFICIARY = re.compile(r"Beneficiary(?: Account)?(?: Title| Name)?\s*:[:\s]*(.+?)\s+(?:Branch|Transaction|IBAN)\b",
                          re.IGNORECASE)
# "spent Rs. 375 at SHOPIFY* 6080 SINGAPORE SG", "sent Rs. 2,500 to Chainfore (Private) Limited 💸", "got ... from Ali".
# Stops at a joining word, sentence end or emoji; never "to your account" / "to this email" / "at 0211..." style text.
_MERCHANT = re.compile(
    r"\b(?:at|to|from|@)\s+(?!(?:your|you|this|the|our|us|a|an|any|my)\b)"
    r"([A-Za-z0-9][A-Za-z0-9&'().*/+\- ]{1,60}?)"
    r"(?=\s+(?:on|dated|via|using|from|ref|for|with|and|or|has|have|is|was)\b|[.,;:!\n](?:\s|$)|[^A-Za-z0-9&'().*/+\- ]|$)",
    re.IGNORECASE)
_LAST4 = re.compile(r"(?:\*{2,}|x{2,}|X{2,}|ending\s+(?:in\s+)?|a/c\s*no\.?\s*\S*?)(\d{4})\b")


def _text_from_payload(payload: dict) -> str:
    parts, stack = [], [payload]
    while stack:
        p = stack.pop()
        stack.extend(p.get("parts") or [])
        data = (p.get("body") or {}).get("data")
        if not data:
            continue
        raw = base64.urlsafe_b64decode(data + "===").decode("utf-8", "ignore")
        if p.get("mimeType") == "text/html":
            raw = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
        parts.append(raw)
    return re.sub(r"\s+", " ", " ".join(parts))[:6000]


def tidy_merchant(name: str) -> str:
    """Card-network descriptors to a readable name: "ANTHROPIC* CLAUDE SUB +14152360599 US" -> "Anthropic Claude Sub"."""
    name = re.sub(r"[xX*]{2,}\d*|\*", " ", name)  # masked account numbers ("ALFALAH-xxx9816"), "SHOPIFY*"
    name = re.sub(r"\+?\d[\d\-]{3,}", " ", name)  # reference numbers, phone numbers
    name = re.sub(r"\s+", " ", name).strip(" .,-/")
    name = re.sub(r"\s+[A-Z]{2}$", "", name) if re.search(r"\s[A-Z]{2}$", name) and name.isupper() else name
    if not re.search(r"[A-Za-z]{2}", name) or _NOT_A_NAME.search(name):
        return ""
    if name.isupper():  # "TOTAL PARCO KARACHI" -> "Total Parco Karachi"; short ones are abbreviations (KFC, DHA)
        name = " ".join(w if len(w) <= 3 else w.title() for w in name.split())
    return name


def find_merchant(subject: str, text: str = "") -> str:
    """Shop or person a transaction was with; the subject line is the most reliable place to look. Only the start
    of the body is read: footers ("contact us at ...", disclaimers) are never a merchant."""
    text = text[:400]
    beneficiary = _BENEFICIARY.search(text)
    if beneficiary and tidy_merchant(beneficiary.group(1)):
        return tidy_merchant(beneficiary.group(1))[:80]
    for source in (subject, text):
        for m in _MERCHANT.finditer(source):
            name = tidy_merchant(m.group(1))
            if name:
                return name[:80]
    return ""


def regex_parse(text: str) -> dict | None:
    amounts = _AMOUNT.findall(text)
    if not amounts:
        return None
    debit, credit = _DEBIT.search(text), _CREDIT.search(text)
    if bool(debit) == bool(credit):
        # Both or neither: take whichever verb comes first.
        if not debit and not credit:
            return None
        direction = "debit" if debit.start() < credit.start() else "credit"
    else:
        direction = "debit" if debit else "credit"
    bal = _BAL.search(text)
    amount = Decimal(amounts[0].replace(",", ""))
    if bal and bal.group(1).replace(",", "") == amounts[0].replace(",", "") and len(amounts) > 1:
        amount = Decimal(amounts[1].replace(",", ""))
    last4 = _LAST4.search(text)
    return {
        "is_transaction": True, "amount": float(amount), "direction": direction,
        "merchant": find_merchant(text),
        "balance_after": float(bal.group(1).replace(",", "")) if bal else None,
        "last4": last4.group(1) if last4 else None,
    }


async def llm_parse(subject: str, text: str) -> dict | None:
    return await complete_json(
        "You read Pakistani bank / wallet alert emails and extract one transaction. Reply JSON: "
        '{"is_transaction": bool, "amount": number, "direction": "debit"|"credit", "merchant": string, '
        '"balance_after": number|null, "last4": string|null, "channel": "card"|"transfer"|"atm"|"online"|"bill"|"other", '
        '"is_income": bool}. Promotional emails, OTPs and statements are not transactions.',
        f"Subject: {subject}\n\n{text[:3500]}",
        max_tokens=250,
    )


async def parse_email(subject: str, text: str) -> dict | None:
    if re.search(r"\b(OTP|one[- ]time password|verification code)\b", subject + text[:300], re.IGNORECASE):
        return None
    fast = regex_parse(f"{subject}. {text}")
    if fast:
        # A subject that already says what it is ("Cash withdrawal ...") has no shop: don't dig one out of the body.
        fast["merchant"] = find_merchant(subject) or ("" if transaction_kind(subject) else find_merchant("", text))
    if fast and (fast["merchant"] or transaction_kind(subject)):
        return fast
    smart = await llm_parse(subject, text)
    if smart and smart.get("is_transaction") and smart.get("amount"):
        return smart
    return fast


# ---------------------------------------------------------------- sync

async def sync_connection(conn_id: uuid.UUID, user_id: uuid.UUID) -> int:
    """Fetch new alert emails from the user's banks and turn them into transactions."""
    created = 0
    async with scoped_session(user_id, "user") as s:
        conn = await s.get(EmailConnection, conn_id)
        if not conn or conn.status == "revoked":
            return 0
        banks = (await s.execute(
            select(Bank).where(Bank.id.in_(select(BankAccount.bank_id).union(select(Card.bank_id))))
        )).scalars().all()
        domains = sorted({d for b in banks for d in b.email_domains})
        accounts = list((await s.execute(select(BankAccount))).scalars())
        if not domains:
            # Inboxes are connected before onboarding names any bank: wait, so the history is still fetched later.
            return 0
        try:
            token = await _access_token(conn)
        except PermissionError as exc:
            conn.status, conn.last_error = "error", str(exc)
            return 0
        # A bank added since the last check gets its history too (already-seen emails are skipped below).
        newest_bank = max([a.created_at for a in accounts] + list((await s.execute(select(Card.created_at))).scalars()))
        since = conn.last_synced_at - timedelta(hours=2) if conn.last_synced_at and newest_bank < conn.last_synced_at \
            else datetime.combine(conn.sync_from or datetime.now(UTC).date(), datetime.min.time(), UTC)
        sources = f"from:({' OR '.join(domains)})"
        if settings.test_tools_enabled:
            # Simulated alerts come from our SMTP account, not the bank's domain.
            sources = f'({sources} OR subject:"{TEST_ALERT_SUBJECT}")'
        query = f"{sources} after:{int(since.timestamp())}"
        seen = set((await s.execute(select(IngestedEmail.external_id).where(
            IngestedEmail.connection_id == conn.id))).scalars())
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=30, headers=headers) as c:
            ids, page = [], None
            while len(ids) < 300:
                params = {"q": query, "maxResults": 100}
                if page:
                    params["pageToken"] = page
                r = await c.get(f"{GMAIL}/messages", params=params)
                r.raise_for_status()
                body = r.json()
                ids += [m["id"] for m in body.get("messages", [])]
                page = body.get("nextPageToken")
                if not page:
                    break
            for mid in reversed(ids):  # oldest first so balances end up current
                if mid in seen:
                    continue
                r = await c.get(f"{GMAIL}/messages/{mid}", params={"format": "full"})
                if r.status_code != 200:
                    continue
                msg = r.json()
                hdrs = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
                subject = hdrs.get("subject", "")
                sender = hdrs.get("from", "").lower()
                text = _text_from_payload(msg["payload"])
                try:
                    when = parsedate_to_datetime(hdrs["date"]) if "date" in hdrs else datetime.now(UTC)
                except (TypeError, ValueError):
                    when = datetime.now(UTC)
                parsed = await parse_email(subject, text)
                status = "ignored"
                if parsed and parsed.get("amount"):
                    bank = next((b for b in banks if any(d in sender for d in b.email_domains)), None) or next(
                        (b for b in banks if b.name.lower() in f"{sender} {subject}".lower()), None)
                    account = _match_account(accounts, bank, parsed.get("last4"))
                    tx = await finance.record_transaction(
                        s, user_id, amount=parsed["amount"], direction=parsed.get("direction", "debit"),
                        occurred_at=when, merchant=parsed.get("merchant") or "", description=subject,
                        account_id=account.id if account else None, channel=parsed.get("channel") or "other",
                        source="gmail", external_id=f"gmail:{mid}", balance_after=parsed.get("balance_after"),
                        is_income=parsed.get("is_income"),
                    )
                    if tx:
                        status, created = "transaction", created + 1
                s.add(IngestedEmail(user_id=user_id, connection_id=conn.id, external_id=mid, status=status,
                                    subject=subject[:500]))
                await s.flush()
        conn.last_synced_at = datetime.now(UTC)
        conn.last_error = None
    if created:
        await notify(user_id, "system", "Transactions updated",
                     f"{created} new transaction{'s' if created > 1 else ''} picked up from your bank emails.",
                     push=False)
    return created


def _match_account(accounts: list[BankAccount], bank: Bank | None, last4: str | None) -> BankAccount | None:
    if last4:
        for a in accounts:
            if a.last4 == last4:
                return a
    if bank:
        same = [a for a in accounts if a.bank_id == bank.id]
        if same:
            return next((a for a in same if a.is_primary), same[0])
    return None


async def sync_all() -> None:
    async with system_session() as s:
        rows = (await s.execute(select(EmailConnection.id, EmailConnection.user_id)
                                .where(EmailConnection.status == "active"))).all()
    for conn_id, user_id in rows:
        try:
            await sync_connection(conn_id, user_id)
        except Exception as exc:
            log.warning("gmail sync failed for %s: %s", conn_id, exc)
            async with scoped_session(user_id, "user") as s:
                conn = await s.get(EmailConnection, conn_id)
                if conn:
                    conn.last_error = str(exc)[:500]
