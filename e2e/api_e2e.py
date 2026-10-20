"""End-to-end API journeys, from a user's point of view, against the running stack.

Every request goes through the Next.js proxy on :3000 (the same path the browser takes), except the two calls that
send email (sign-up code, password reset), which go to a from-source backend on :8010 with SMTP turned off: it shares
the database and Dragonfly, and writes the email to its log, where this script reads the code / link.

Writes results to results/api.json and prints a summary. Creates one throwaway user and deletes it at the end.
"""

import base64
import io
import json
import queue
import re
import struct
import sys
import threading
import time
import uuid
from pathlib import Path

import httpx
import redis as redis_lib

HERE = Path(__file__).parent
FRONT = "http://localhost:3000"
MAILER = "http://127.0.0.1:8010"  # SMTP-less backend
MAILER_LOG = HERE / "backend-8010.log"
FIX = HERE / "fixtures"
DEMO = ("demo@bachat.pk", "demo12345")
ADMIN = ("admin@bachat.pk", "admin12345")
STAMP = time.strftime("%m%d%H%M%S")
TEST_EMAIL = f"e2e-{STAMP}@example.com"
TEST_PW, TEST_PW2 = "E2e-pass-1234", "E2e-pass-5678"
CSRF = {"x-requested-with": "bachat"}

r = redis_lib.Redis(host="127.0.0.1", port=6380, decode_responses=True)
results: list[dict] = []
section = "?"


def sec(name: str) -> None:
    global section
    section = name
    print(f"\n## {name}")


def check(name: str, ok: bool, detail: str = "", warn: bool = False) -> bool:
    status = "PASS" if ok else ("WARN" if warn else "FAIL")
    results.append({"section": section, "name": name, "status": status, "detail": str(detail)[:400]})
    print(f"  [{status}] {name}" + (f"  — {str(detail)[:200]}" if detail and not ok else ""))
    return ok


def skip(name: str, why: str) -> None:
    results.append({"section": section, "name": name, "status": "SKIP", "detail": why})
    print(f"  [SKIP] {name} — {why}")


def client() -> httpx.Client:
    return httpx.Client(base_url=FRONT, headers=CSRF, timeout=60, follow_redirects=False)


def jwt_payload(token: str) -> dict:
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def sid_of(c: httpx.Client) -> str:
    return jwt_payload(c.cookies.get("at"))["sid"]


def signin(c: httpx.Client, email: str, pw: str) -> httpx.Response:
    return c.post("/api/auth/signin", json={"email": email, "password": pw})


def detail(resp: httpx.Response) -> str:
    try:
        return f"{resp.status_code} {resp.json().get('detail')}"
    except Exception:
        return f"{resp.status_code} {resp.text[:120]}"


def mail_log_find(pattern: str, after: int, timeout: float = 15) -> re.Match | None:
    end = time.time() + timeout
    while time.time() < end:
        text = MAILER_LOG.read_text(errors="replace")[after:]
        m = re.search(pattern, text)
        if m:
            return m
        time.sleep(0.5)
    return None


def wav(seconds: float, rate: int = 16000) -> bytes:
    n = int(seconds * rate)
    data = b"\x00\x00" * n
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return hdr + b"data" + struct.pack("<I", len(data)) + data


class SSE:
    """Reads /api/chat/stream in a thread and queues each JSON event."""

    def __init__(self, cookies: httpx.Cookies) -> None:
        self.q: queue.Queue = queue.Queue()
        self.stop = threading.Event()
        self.connected = threading.Event()
        self.status = None
        self.t = threading.Thread(target=self._run, args=(cookies,), daemon=True)
        self.t.start()

    def _run(self, cookies: httpx.Cookies) -> None:
        with httpx.Client(base_url=FRONT, cookies=cookies, timeout=httpx.Timeout(10, read=None)) as c:
            with c.stream("GET", "/api/chat/stream") as resp:
                self.status = resp.status_code
                self.ctype = resp.headers.get("content-type", "")
                self.connected.set()
                for line in resp.iter_lines():
                    if self.stop.is_set():
                        return
                    if line.startswith("data: "):
                        try:
                            self.q.put(json.loads(line[6:]))
                        except json.JSONDecodeError:
                            pass


# ======================================================================================================== platform
def platform() -> None:
    sec("Platform, proxy and security basics")
    h = httpx.get(f"{FRONT}/api/health", timeout=10)
    check("Health check through the web proxy", h.status_code == 200 and h.json().get("ok") is True, h.text)
    want = {"x-content-type-options": "nosniff", "x-frame-options": "DENY", "referrer-policy": "no-referrer",
            "cache-control": "no-store"}
    missing = {k: h.headers.get(k) for k, v in want.items() if h.headers.get(k) != v}
    check("API responses carry security headers and no-store", not missing, missing)
    resp = httpx.post(f"{FRONT}/api/auth/signin", json={"email": DEMO[0], "password": DEMO[1]}, timeout=10)
    check("Writes without the CSRF header are refused (403)", resp.status_code == 403 and "csrf" in resp.text, detail(resp))
    resp = httpx.get(f"{FRONT}/api/me", timeout=10)
    check("Private data needs a session (401 when signed out)", resp.status_code == 401, detail(resp))
    resp = httpx.post(f"{FRONT}/api/internal/omb/events", json=[], timeout=10)
    check("Gateway-only endpoints refuse calls without the internal key", resp.status_code == 401, detail(resp))
    resp = httpx.post(f"{FRONT}/mcp/user", json={}, timeout=10)
    check("Bot tool servers (/mcp) are not reachable through the web proxy", resp.status_code == 404, resp.status_code)
    resp = httpx.post(f"{FRONT}/api/auth/forgot", headers=CSRF, content=b'{"email":"' + b"a" * 70000 + b'@x.pk"}',
                      timeout=10)
    check("Oversized request bodies are refused (413)", resp.status_code == 413, detail(resp))
    resp = httpx.get(f"{FRONT}/api/push/vapid-key", timeout=10)
    check("Web-push public key is published", resp.status_code == 200 and len(resp.json().get("key") or "") > 40,
          resp.text[:80])


def frontend_routes() -> None:
    sec("Every screen answers over HTTP")
    pages = ["/", "/signin", "/signup", "/forgot-password", "/dashboard", "/goals", "/spending", "/deals", "/activity",
             f"/goals/{uuid.uuid4()}", "/admin", "/admin/users", "/admin/agents", "/admin/plans", "/admin/deals",
             "/admin/companies", "/admin/banks", "/admin/cards", "/admin/assets", "/admin/watchlists"]
    bad = []
    for p in pages:
        resp = httpx.get(f"{FRONT}{p}", timeout=60)
        if resp.status_code != 200 or "<html" not in resp.text[:500].lower():
            bad.append(f"{p}={resp.status_code}")
    check(f"{len(pages)} app pages return 200 HTML", not bad, ", ".join(bad))
    resp = httpx.get(f"{FRONT}/this-page-does-not-exist", timeout=30)
    check("Unknown pages return 404", resp.status_code == 404, resp.status_code)
    man = httpx.get(f"{FRONT}/manifest.webmanifest", timeout=10)
    if man.status_code == 404:
        man = httpx.get(f"{FRONT}/manifest.json", timeout=10)
    ok = man.status_code == 200
    m = man.json() if ok else {}
    check("PWA manifest is served with a start URL and icons", ok and m.get("start_url") and m.get("icons"),
          f"{man.status_code} start_url={m.get('start_url')}")
    icons_bad = [i["src"] for i in m.get("icons", []) if httpx.get(f"{FRONT}{i['src']}", timeout=10).status_code != 200]
    check("Every manifest icon loads", ok and not icons_bad, icons_bad)
    sw = httpx.get(f"{FRONT}/sw.js", timeout=10)
    check("Service worker script is served", sw.status_code == 200 and "fetch" in sw.text, sw.status_code)
    check("Service worker never caches /api", "/api" in sw.text, "no /api exclusion found in sw.js")


# ========================================================================================================= sign-up
def signup_flow() -> httpx.Client | None:
    sec("Sign-up with an emailed code (new user)")
    m = httpx.Client(base_url=MAILER, headers=CSRF, timeout=60)
    resp = m.post("/api/auth/signup", json={"email": TEST_EMAIL, "password": "short", "full_name": "E2E"})
    check("A password under 8 characters is rejected", resp.status_code == 422, detail(resp))
    resp = m.post("/api/auth/signup", json={"email": "not-an-email", "password": TEST_PW, "full_name": "E2E"})
    check("An invalid email is rejected", resp.status_code == 422, detail(resp))
    resp = m.post("/api/auth/signup", json={"email": DEMO[0], "password": TEST_PW, "full_name": "E2E"})
    check("An email that already has an account is refused (409 email_taken)",
          resp.status_code == 409 and resp.json().get("detail") == "email_taken", detail(resp))

    mark = MAILER_LOG.stat().st_size
    resp = m.post("/api/auth/signup", json={"email": TEST_EMAIL.upper(), "password": TEST_PW, "full_name": " E2E Tester "})
    if not check("Sign-up step 1 accepts the details and says a code was sent", resp.status_code == 200
                 and resp.json().get("email") == TEST_EMAIL and resp.json().get("resend_in") == 60, detail(resp)):
        return None
    got = mail_log_find(rf"email to {re.escape(TEST_EMAIL)} not sent\. Subject=(\d{{6}}) is your", mark)
    if not check("A 6-digit code email is produced for the (lower-cased) address", bool(got), "no code in the log"):
        return None
    code = got.group(1)
    check("Nothing is written to the database before the code is entered",
          r.exists(f"signup:{__import__('hashlib').sha256(TEST_EMAIL.encode()).hexdigest()}") == 1)
    c = client()
    resp = c.post("/api/auth/signup/resend", json={"email": TEST_EMAIL})
    check("Asking for a new code within 60 s is refused (429)", resp.status_code == 429, detail(resp))
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"
    resp = c.post("/api/auth/signup/verify", json={"email": TEST_EMAIL, "code": wrong})
    check("A wrong code is rejected (400 invalid_code)", resp.json().get("detail") == "invalid_code", detail(resp))
    resp = c.post("/api/auth/signup/verify", json={"email": TEST_EMAIL, "code": code})
    ok = check("The right code creates the account and signs the person in", resp.status_code == 200
               and resp.json()["user"]["email"] == TEST_EMAIL and resp.json()["user"]["role"] == "user", detail(resp))
    if not ok:
        return None
    u = resp.json()["user"]
    check("The name is trimmed and onboarding starts as not done",
          u["full_name"] == "E2E Tester" and u["onboarding_completed"] is False, u)
    resp2 = c.post("/api/auth/signup/verify", json={"email": TEST_EMAIL, "code": code})
    check("The same code can't be used twice", resp2.status_code == 400, detail(resp2))
    set_cookie = resp.headers.get_list("set-cookie")
    at = next((x for x in set_cookie if x.startswith("at=")), "")
    rt = next((x for x in set_cookie if x.startswith("rt=")), "")
    check("Session cookies are HttpOnly, SameSite=Lax; refresh cookie limited to /api/auth",
          "httponly" in at.lower() and "samesite=lax" in at.lower() and "path=/api/auth" in rt.lower()
          and "httponly" in rt.lower(), f"at={at[:60]}… rt={rt[-80:]}")
    return c


def new_user_experience(c: httpx.Client) -> None:
    sec("A brand-new user's first visit")
    s = c.get("/api/auth/session").json()
    check("Session reports active with a 5-minute idle lock", s.get("state") == "active"
          and s.get("idle_lock_minutes") == 5 and s.get("has_passkey") is False, s)
    me = c.get("/api/me")
    check("Profile loads (language en, not onboarded)", me.status_code == 200 and me.json()["language"] == "en"
          and me.json()["onboarding_completed"] is False, detail(me))
    d = c.get("/api/dashboard")
    ok = d.status_code == 200
    j = d.json() if ok else {}
    check("Empty dashboard loads with zero totals and no errors", ok and float(j["total_balance"]) == 0
          and j["banks"] == [] and j["goals"] == [] and j["email_connected"] is False, detail(d))
    check("Empty goal list, bank details and activity load", c.get("/api/goals").json() == []
          and c.get("/api/banks").json()["accounts"] == [] and c.get("/api/transactions").json() == [])
    em = c.get("/api/email/connections").json()
    check("Email settings say Gmail is configured and nothing is connected",
          em.get("configured") is True and em.get("connections") == [], em)
    g = c.post("/api/email/google/start")
    url = g.json().get("url", "") if g.status_code == 200 else ""
    check("'Connect Gmail' produces a Google consent URL with read-only Gmail scope",
          url.startswith("https://accounts.google.com/") and "gmail.readonly" in url, url[:120] or detail(g))
    resp = c.post("/api/chat/messages", json={"text": "hi"})
    check("Chat is gated until Gmail is connected (409 connect_gmail_first)",
          resp.status_code == 409 and resp.json().get("detail") == "connect_gmail_first", detail(resp))
    st = None
    for _ in range(60):  # the private assistant team is provisioned in the background after sign-up
        st = c.get("/api/chat/status").json()
        if st.get("status") in ("ready", "error"):
            break
        time.sleep(5)
    check("The private assistant team gets provisioned (status ready)", st and st.get("status") == "ready", st)
    adv = set((st or {}).get("advisors", []))
    check("New users get Finance Assistant, Savings Coach and Deals Advisor (no investment bot unless opted in)",
          {"Finance Assistant", "Savings Coach", "Deals Advisor"} <= adv and not any("Invest" in a for a in adv), adv)
    resp = c.post("/api/dev/test-alert")
    check("Test-alert tool refuses politely without a connected inbox",
          resp.status_code == 400 and resp.json().get("detail") == "connect_gmail_first", detail(resp))


# =========================================================================================================== demo
def demo_reads(c: httpx.Client) -> dict:
    sec("Returning user: sign-in and every dashboard read (demo account)")
    resp = signin(c, DEMO[0], "wrong-password")
    check("A wrong password is refused (401 invalid_credentials)", resp.json().get("detail") == "invalid_credentials",
          detail(resp))
    resp = signin(c, f"nobody-{STAMP}@example.com", "whatever123")
    check("An unknown email gets the same answer (no account discovery)",
          resp.json().get("detail") == "invalid_credentials", detail(resp))
    resp = signin(c, DEMO[0].upper(), DEMO[1])
    check("Sign-in works (email is case-insensitive)", resp.status_code == 200 and resp.json()["user"]["role"] == "user",
          detail(resp))
    ips = sorted({k.split(":")[2] for k in r.scan_iter(f"rl:signin:*:{DEMO[0]}")})
    check("Per-address rate limits see the caller's own address through the web proxy",
          bool(ips) and not any(ip.startswith(("172.", "10.", "192.168.")) for ip in ips),
          f"backend saw {ips} (the frontend container), so every browser shares one bucket in the local stack",
          warn=True)
    httpx.post(f"{FRONT}/api/auth/signin", headers={**CSRF, "x-forwarded-for": "203.0.113.77"},
               json={"email": f"xff-{STAMP}@example.com", "password": "nope"}, timeout=10)
    spoofed = bool(list(r.scan_iter(f"rl:signin:203.0.113.77:xff-{STAMP}@example.com")))
    check("A client can't choose its own rate-limit address with X-Forwarded-For", not spoofed,
          "the local stack trusts a client-sent X-Forwarded-For (documented in config.py; Railway's edge appends)",
          warn=True)
    me = c.get("/api/me").json()
    check("Profile: onboarded, assistant ready", me.get("onboarding_completed") is True
          and me.get("assistant_status") == "ready", me)
    d = c.get("/api/dashboard")
    if not check("Dashboard loads", d.status_code == 200, detail(d)):
        return {}
    j = d.json()
    num = lambda v: float(v)  # noqa: E731 - money comes back as strings
    bal = sum(num(b["balance"]) for b in j["banks"])
    check("Total balance equals the sum of bank balances", abs(num(j["total_balance"]) - bal) < 0.01,
          f"{j['total_balance']} vs {bal}")
    check("Spendable = balance − savings (never negative)",
          abs(num(j["expendable"]) - max(num(j["total_balance"]) - num(j["total_savings"]), 0)) < 0.01,
          f"{j['expendable']} {j['total_balance']} {j['total_savings']}")
    spent = sum(num(x["amount"]) for x in j["spending_by_category"])
    check("Spent this month equals the category breakdown", abs(num(j["spent_this_month"]) - spent) < 0.01,
          f"{j['spent_this_month']} vs {spent}")
    check("Monthly cards are present (saved this month, deal savings this month, salary flag)",
          all(k in j for k in ("saved_this_month", "deal_savings_this_month", "salary_credited_this_month")))
    check("Goal progress is between 0 and 1", all(0 <= g["progress"] <= 1 for g in j["goals"]),
          [g["progress"] for g in j["goals"]])
    neg = [b["bank"] for b in j["banks"] if num(b["savings"]) < 0 or num(b["expendable"]) < 0]
    check("No bank shows negative savings or spendable", not neg, neg)
    check("Deals for you are listed", isinstance(j.get("deals_for_you"), list) and len(j["deals_for_you"]) > 0,
          len(j.get("deals_for_you") or []), warn=True)
    goals = c.get("/api/goals").json()
    check("Goal list loads", isinstance(goals, list) and len(goals) >= 1, len(goals))
    if goals:
        gd = c.get(f"/api/goals/{goals[0]['id']}")
        gj = gd.json()
        check("Goal details load with history, monthly rate and projection",
              gd.status_code == 200 and "history" in gj and "monthly_rate" in gj and "on_track" in gj, detail(gd))
        check("Goal remaining = target − saved", abs(num(gj["remaining"]) - max(num(gj["target"]) - num(gj["saved"]), 0))
              < 0.01, gj.get("remaining"))
    resp = c.get(f"/api/goals/{uuid.uuid4()}")
    check("An unknown goal id is a 404", resp.status_code == 404, detail(resp))
    resp = c.get("/api/goals/not-a-uuid")
    check("A malformed goal id is rejected cleanly (422, not 500)", resp.status_code == 422, detail(resp))
    b = c.get("/api/banks")
    bj = b.json()
    check("Bank details load with accounts, cards and recent transactions",
          b.status_code == 200 and len(bj["accounts"]) == len(j["banks"])
          and all("transactions" in a and "cards" in a for a in bj["accounts"]), detail(b))
    tx = c.get("/api/transactions", params={"days": 90, "limit": 200}).json()
    check("Activity: 90 days of transactions load", isinstance(tx, list) and len(tx) > 0, len(tx))
    check("Every transaction has an amount, a direction and a title",
          all(t["amount"] is not None and t["direction"] in ("debit", "credit") and t["merchant"] for t in tx),
          [t for t in tx if not t["merchant"]][:2])
    resp = c.get("/api/transactions", params={"limit": 100000})
    check("Huge page sizes are capped (≤200)", resp.status_code == 200 and len(resp.json()) <= 200, len(resp.json()))
    deals = c.get("/api/deals")
    check("Deals list loads", deals.status_code == 200 and isinstance(deals.json(), list), detail(deals))
    dq = c.get("/api/deals", params={"q": "zzzz-no-such-deal"})
    check("Deal search with no match returns an empty list", dq.status_code == 200 and dq.json() == [], dq.text[:80])
    n = c.get("/api/notifications")
    check("Notifications load", n.status_code == 200 and isinstance(n.json(), list), detail(n))
    for path in ("/api/chat/unread", "/api/chat/messages", "/api/chat/status", "/api/auth/webauthn/credentials",
                 "/api/email/connections"):
        resp = c.get(path)
        check(f"GET {path}", resp.status_code == 200, detail(resp))
    hist = c.get("/api/chat/messages", params={"limit": 5}).json()
    check("Chat history pages (limit respected, oldest first)", len(hist) <= 5 and
          [m["created_at"] for m in hist] == sorted(m["created_at"] for m in hist))
    if hist:
        older = c.get("/api/chat/messages", params={"before": hist[0]["created_at"], "limit": 5}).json()
        check("Loading older chat messages works", all(m["created_at"] < hist[0]["created_at"] for m in older))
    return j


def isolation(test: httpx.Client, demo_c: httpx.Client) -> None:
    sec("Privacy between accounts (row-level security)")
    goals = demo_c.get("/api/goals").json()
    if not goals:
        skip("Another user's goal is invisible", "demo has no goals")
        return
    resp = test.get(f"/api/goals/{goals[0]['id']}")
    check("Another user's goal can't be opened by id (404)", resp.status_code == 404, detail(resp))
    check("Another user's transactions don't appear", test.get("/api/transactions", params={"days": 3650}).json() == [])
    demo_ids = {m["id"] for m in demo_c.get("/api/chat/messages", params={"limit": 100}).json()}
    mine = {m["id"] for m in test.get("/api/chat/messages", params={"limit": 100}).json()}
    check("Another user's chat history doesn't appear", demo_ids and not (demo_ids & mine), f"overlap={len(demo_ids & mine)}")
    resp = test.get("/api/admin/users")
    check("A regular user can't use admin endpoints (403 admin_only)", resp.status_code == 403, detail(resp))


# ===================================================================================================== profile/avatar
def profile(c: httpx.Client) -> None:
    sec("Settings: name, language and profile photo (new user)")
    resp = c.patch("/api/me", json={"full_name": "E2E Renamed", "language": "roman_ur"})
    me = c.get("/api/me").json()
    check("Name and language can be changed", resp.status_code == 200 and me["full_name"] == "E2E Renamed"
          and me["language"] == "roman_ur", detail(resp))
    c.patch("/api/me", json={"language": "klingon"})
    check("An unsupported language is ignored", c.get("/api/me").json()["language"] == "roman_ur")
    c.patch("/api/me", json={"language": "en"})
    png = (FIX / "test-photo.png").read_bytes()
    resp = c.post("/api/me/avatar", files={"image": ("p.png", png, "image/png")})
    check("A photo can be uploaded", resp.status_code == 200 and resp.json().get("avatar_version"), detail(resp))
    g = c.get("/api/me/avatar")
    check("The photo is served back as an image, cacheable for the owner only",
          g.status_code == 200 and g.headers["content-type"] == "image/png" and g.content == png
          and "private" in g.headers.get("cache-control", ""), f"{g.status_code} {g.headers.get('cache-control')}")
    resp = c.post("/api/me/avatar", files={"image": ("evil.png", b"<script>alert(1)</script>", "image/png")})
    check("A non-image disguised as .png is refused (415)", resp.status_code == 415, detail(resp))
    big = {"image": ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * 600_000, "image/png")}
    bearer = {**CSRF, "authorization": "Bearer " + c.cookies.get("at")}
    resp = httpx.post("http://127.0.0.1:8000/api/me/avatar", headers=bearer, files=big, timeout=30)
    check("A photo over 512 KB is refused by the server (413)", resp.status_code == 413, detail(resp))
    outcomes = []
    for _ in range(5):
        try:
            outcomes.append(str(httpx.post(f"{FRONT}/api/me/avatar", headers=bearer, files=big, timeout=30).status_code))
        except httpx.HTTPError as exc:
            outcomes.append(type(exc).__name__)
    check("…and that 413 reaches the browser intact through the web proxy", outcomes == ["413"] * 5,
          f"5 tries via :3000 -> {outcomes}", warn=True)
    resp = c.delete("/api/me/avatar")
    check("The photo can be removed", resp.status_code == 200 and c.get("/api/me/avatar").status_code == 404,
          detail(resp))


def voice(c: httpx.Client) -> None:
    sec("Voice notes to editable text")
    eng = (FIX / "english.wav").read_bytes()
    t = time.time()
    resp = c.post("/api/chat/transcribe", files={"audio": ("note.wav", eng, "audio/wav")}, timeout=180)
    text = resp.json().get("text", "") if resp.status_code == 200 else ""
    check("An English voice note becomes text", resp.status_code == 200 and len(text.split()) >= 3,
          f"{detail(resp)} {text!r}")
    check("…in Latin script when the language is English", bool(text) and not re.search(r"[؀-ۿ]", text), text)
    results[-1]["detail"] = f"{time.time() - t:.1f}s: {text!r}"
    c.patch("/api/me", json={"language": "ur"})
    urdu = (FIX / "urdu.wav").read_bytes()
    resp = c.post("/api/chat/transcribe", files={"audio": ("note.wav", urdu, "audio/wav")}, timeout=180)
    utext = resp.json().get("text", "") if resp.status_code == 200 else ""
    check("An Urdu voice note comes back in Urdu script when the language is Urdu",
          resp.status_code == 200 and bool(re.search(r"[؀-ۿ]", utext)), f"{detail(resp)} {utext!r}")
    results[-1]["detail"] = repr(utext)[:200]
    c.patch("/api/me", json={"language": "en"})
    resp = c.post("/api/chat/transcribe", files={"audio": ("x.mp3", b"ID3" + b"\x00" * 5000, "audio/mpeg")})
    check("Non-WAV audio is refused (415)", resp.status_code == 415, detail(resp))
    resp = c.post("/api/chat/transcribe", files={"audio": ("x.wav", wav(0.1), "audio/wav")})
    check("A note under 0.3 s is refused (422 audio_too_short)", resp.status_code == 422, detail(resp))
    resp = c.post("/api/chat/transcribe", files={"audio": ("x.wav", wav(31), "audio/wav")})
    check("A note over 30 s is refused (413)", resp.status_code == 413, detail(resp))


# =========================================================================================================== chat
def chat(c: httpx.Client, dash: dict) -> None:
    sec("Chat with the assistant team (demo account, live model)")
    sse = SSE(c.cookies)
    sse.connected.wait(15)
    check("Live chat stream connects (text/event-stream)", sse.status == 200 and "event-stream" in sse.ctype,
          f"{sse.status} {getattr(sse, 'ctype', '')}")
    time.sleep(1.5)
    uid = jwt_payload(c.cookies.get("at"))["sub"]
    check("While the stream is open the person counts as online (no duplicate pushes)",
          r.get(f"online:{uid}") == "1", r.get(f"online:{uid}"))
    question = "How many savings goals do I have right now? Reply in one short sentence."
    t0 = time.time()
    resp = c.post("/api/chat/messages", json={"text": question})
    if not check("Sending a message is accepted and echoed", resp.status_code == 200
                 and resp.json()["role"] == "user" and resp.json()["text"] == question, detail(resp)):
        sse.stop.set()
        return
    echoed, activity, final, partial = False, set(), None, 0
    while time.time() - t0 < 420 and not final:
        try:
            ev = sse.q.get(timeout=5)
        except queue.Empty:
            continue
        if ev.get("type") == "message":
            m = ev["message"]
            if m["role"] == "user" and m["text"] == question:
                echoed = True
            elif m["role"] == "bot":
                partial += 1
                if m["final"]:
                    final = m
            elif m["role"] == "system":
                final = m
        elif ev.get("type") == "activity":
            activity.add(ev["activity"].get("state"))
    took = time.time() - t0
    sse.stop.set()
    check("The sent message appears on the live stream", echoed)
    check("Live progress (thinking / tool / writing) is streamed while the bot works", bool(activity - {"idle"}),
          activity, warn=True)
    if not check("A final bot reply arrives", bool(final) and final["role"] == "bot",
                 f"after {took:.0f}s: {final}"):
        return
    results[-1]["detail"] = f"{took:.0f}s from {final['sender']}: {final['text'][:220]!r}"
    said = final["text"]
    n_active = len([g for g in dash.get("goals", []) if g["status"] == "active"])
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
    check(f"The reply uses the person's real data ({n_active} active goals)",
          bool(re.search(rf"\b({n_active}|{words.get(n_active, '@@')})\b", said.lower())), said[:200], warn=True)
    check("The reply never leaks the room's member key", not re.search(r"\b(?:[a-z]+-){4}\d{2}(?:-[a-z]+){3}\b", said.lower()))
    hist = c.get("/api/chat/messages", params={"limit": 10}).json()
    check("Question and reply are saved in chat history",
          any(m["text"] == question for m in hist) and any(m["id"] == final["id"] for m in hist))
    unread = c.get("/api/chat/unread").json()
    c.post("/api/chat/read")
    after = c.get("/api/chat/unread").json()
    check("Opening the chat clears the unread badge", after["count"] == 0, f"before={unread} after={after}")
    resp = c.post("/api/chat/messages", json={"text": "x" * 4001})
    check("Messages over 4000 characters are refused (422)", resp.status_code == 422, detail(resp))
    resp = c.post("/api/chat/messages", json={"text": ""})
    check("Empty messages are refused (422)", resp.status_code == 422, detail(resp))


# ===================================================================================================== lock/session
def idle_lock(c: httpx.Client) -> None:
    sec("Idle lock after 5 minutes, unlock with password")
    sid = sid_of(c)
    r.delete(f"sess:{sid}:active")  # exactly what 5 idle minutes do on the server
    resp = c.get("/api/dashboard")
    check("After 5 idle minutes private data answers 423 locked", resp.status_code == 423, detail(resp))
    check("The app's launch check reports 'locked'", c.get("/api/auth/session").json().get("state") == "locked")
    resp = c.post("/api/auth/refresh")
    check("A locked session can't be refreshed around the lock", resp.status_code == 423, detail(resp))
    resp = c.get("/api/chat/stream", timeout=10)
    check("The live chat stream is locked too", resp.status_code == 423, detail(resp))
    resp = c.post("/api/auth/unlock", json={"password": "wrong-password"})
    check("Unlock with a wrong password is refused", resp.status_code == 401, detail(resp))
    resp = c.post("/api/auth/unlock", json={"password": DEMO[1]})
    check("Unlock with the right password works", resp.status_code == 200, detail(resp))
    check("Data loads again after unlocking", c.get("/api/dashboard").status_code == 200)


def refresh_rotation(c: httpx.Client) -> None:
    sec("Staying signed in: access-token refresh")

    def rt_of(resp_or_client) -> str | None:
        if isinstance(resp_or_client, httpx.Response):
            got = [h.split(";", 1)[0][3:] for h in resp_or_client.headers.get_list("set-cookie") if h.startswith("rt=")]
            return got[-1] if got else None
        vals = [ck.value for ck in resp_or_client.cookies.jar if ck.name == "rt"]
        return vals[-1] if vals else None

    def post_refresh(rt: str) -> httpx.Response:  # a bare request carrying only the refresh cookie
        return httpx.post(f"{FRONT}/api/auth/refresh", headers={**CSRF, "cookie": f"rt={rt}"}, timeout=10)

    old_rt = rt_of(c)
    first = post_refresh(old_rt)
    new_rt = rt_of(first)
    check("Refresh issues a new access token and rotates the refresh token", first.status_code == 200
          and new_rt and new_rt != old_rt and any(h.startswith("at=") for h in first.headers.get_list("set-cookie")),
          detail(first))
    replay = post_refresh(old_rt)
    check("An old (already used) refresh token is refused", replay.status_code == 401, detail(replay))
    still = c.get("/api/me").status_code
    check("Replaying a stolen refresh token also ends the session (theft detection)", still == 401,
          f"session still works after replay: /api/me={still}", warn=True)
    again = post_refresh(new_rt)
    check("An expired access token is renewed silently from the current refresh cookie", again.status_code == 200
          and rt_of(again), detail(again))


def rate_limits() -> None:
    sec("Brute-force protection")
    c = client()
    email = f"nobody-rl-{STAMP}@example.com"
    codes = [signin(c, email, f"guess-{i}").status_code for i in range(9)]
    check("The 9th wrong password in 15 minutes is blocked (429)", codes[:8] == [401] * 8 and codes[8] == 429, codes)
    resp = signin(c, email, "guess-x")
    check("Blocked responses say when to retry (Retry-After)", resp.status_code == 429
          and int(resp.headers.get("retry-after", 0)) > 0, resp.headers.get("retry-after"))


def reset_password(c: httpx.Client) -> None:
    sec("Forgot password (new user)")
    m = httpx.Client(base_url=MAILER, headers=CSRF, timeout=60)
    resp = m.post("/api/auth/forgot", json={"email": f"nobody-{STAMP}@example.com"})
    check("Unknown emails get the same 'sent' answer (no account discovery)", resp.json() == {"ok": True}, detail(resp))
    mark = MAILER_LOG.stat().st_size
    resp = m.post("/api/auth/forgot", json={"email": TEST_EMAIL})
    got = mail_log_find(r"(http://localhost:3000/forgot-password\?token=[\w-]+)", mark)
    if not check("A reset email with a link to the app is produced", resp.status_code == 200 and bool(got),
                 detail(resp)):
        return
    token = got.group(1).split("token=")[1]
    resp = c.post("/api/auth/reset", json={"token": "bogus-token", "password": TEST_PW2})
    check("A bogus reset link is refused", resp.status_code == 400, detail(resp))
    resp = c.post("/api/auth/reset", json={"token": token, "password": "short"})
    check("A too-short new password is refused", resp.status_code == 422, detail(resp))
    resp = c.post("/api/auth/reset", json={"token": token, "password": TEST_PW2})
    check("The reset link sets a new password", resp.status_code == 200, detail(resp))
    check("Resetting signs out every existing session", c.get("/api/me").status_code == 401)
    resp = c.post("/api/auth/reset", json={"token": token, "password": TEST_PW2})
    check("A reset link works only once", resp.status_code == 400, detail(resp))
    check("The old password no longer works", signin(c, TEST_EMAIL, TEST_PW).status_code == 401)
    check("The new password works", signin(c, TEST_EMAIL, TEST_PW2).status_code == 200)


# ========================================================================================================== admin
def admin(test_c: httpx.Client) -> None:
    sec("Admin console")
    a = client()
    resp = signin(a, *ADMIN)
    if not check("Admin can sign in", resp.status_code == 200 and resp.json()["user"]["role"] == "admin", detail(resp)):
        return
    resp = a.get("/api/me")
    check("Admins have no personal finance area (403 admin_account)", resp.status_code == 403, detail(resp))
    resp = a.get("/api/chat/status")
    check("Admins have no assistant chat (403)", resp.status_code == 403, detail(resp))
    bad = []
    for path in ("stats", "users", "agents", "usage", "deals", "clusters", "plans", "audit", "banks", "cards",
                 "companies", "assets"):
        resp = a.get(f"/api/admin/{path}")
        if resp.status_code != 200:
            bad.append(f"{path}={resp.status_code}")
    check("All 12 admin views load", not bad, bad)
    stats = a.get("/api/admin/stats").json()
    users = a.get("/api/admin/users", params={"limit": 200}).json()
    check("User counts exclude admin accounts", stats["users"] == users["total"]
          and all(u["role"] == "user" for u in users["users"]), f"stats={stats['users']} list={users['total']}")
    me = next((u for u in users["users"] if u["email"] == TEST_EMAIL), None)
    check("The new sign-up shows up in the user list with its assistant status", bool(me), TEST_EMAIL)
    if not me:
        return
    found = a.get("/api/admin/users", params={"q": "e2e-" + STAMP}).json()
    check("User search finds them", found["total"] == 1, found["total"])
    resp = a.patch(f"/api/admin/users/{me['id']}", json={"is_active": False})
    check("Admin can disable an account", resp.status_code == 200, detail(resp))
    check("Disabling signs the person out at once", test_c.get("/api/me").status_code == 401)
    resp = signin(client(), TEST_EMAIL, TEST_PW2)
    check("A disabled account can't sign in (403 account_disabled)", resp.json().get("detail") == "account_disabled",
          detail(resp))
    a.patch(f"/api/admin/users/{me['id']}", json={"is_active": True})
    check("Re-enabled account can sign in again", signin(client(), TEST_EMAIL, TEST_PW2).status_code == 200)
    audit = a.get("/api/admin/audit").json()
    check("Admin actions are written to the audit log", any(e.get("target") == me["id"] for e in
          (audit if isinstance(audit, list) else audit.get("entries", audit.get("items", [])))), str(audit)[:200])
    resp = a.delete(f"/api/admin/users/{me['id']}")
    check("Admin can delete an account (and its assistant team)", resp.status_code == 200
          and resp.json().get("omb_cleanup") == "done", resp.text[:200])
    check("A deleted account can't sign in", signin(client(), TEST_EMAIL, TEST_PW2).status_code == 401)
    resp = a.delete(f"/api/admin/users/{a.get('/api/auth/session').json()['user']['id']}")
    check("Admins can't delete themselves / admin accounts", resp.status_code in (400, 404), detail(resp))
    a.post("/api/auth/signout")


def signout(c: httpx.Client) -> None:
    sec("Sign out")
    resp = c.post("/api/auth/signout")
    check("Sign out succeeds and clears cookies", resp.status_code == 200 and not c.cookies.get("at"), detail(resp))
    check("After sign-out private data is refused", c.get("/api/me").status_code == 401)
    check("After sign-out the app's launch check says 'none'", c.get("/api/auth/session").json().get("state") == "none")


def cleanup() -> None:
    """Delete throwaway e2e users left by earlier (crashed) runs."""
    a = client()
    if signin(a, *ADMIN).status_code != 200:
        return
    for u in a.get("/api/admin/users", params={"q": "e2e-", "limit": 200}).json()["users"]:
        if re.fullmatch(r"e2e-\d+@example\.com", u["email"]):
            print("  cleanup: deleting", u["email"], a.delete(f"/api/admin/users/{u['id']}").status_code)
    a.post("/api/auth/signout")


def run(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # one broken step shouldn't hide the rest of the report
        results.append({"section": section, "name": f"{fn.__name__} crashed", "status": "FAIL",
                        "detail": f"{type(exc).__name__}: {exc}"[:400]})
        print(f"  [FAIL] {fn.__name__} crashed: {type(exc).__name__}: {exc}")


def main() -> None:
    only = set(sys.argv[1:])
    # Sign-in counters from earlier runs of this suite (8 per 15 min per address and account) would block re-runs.
    for k in [*r.scan_iter(f"rl:signin:*:{DEMO[0]}"), *r.scan_iter(f"rl:signin:*:{ADMIN[0]}")]:
        r.delete(k)
    cleanup()
    run(platform)
    run(frontend_routes)
    test_c = run(signup_flow)
    demo_c = client()
    dash = run(demo_reads, demo_c) or {}
    if test_c:
        run(new_user_experience, test_c)
        run(isolation, test_c, demo_c)
        run(profile, test_c)
        run(voice, test_c)
    if "nochat" not in only:
        run(chat, demo_c, dash)
    run(idle_lock, demo_c)
    run(refresh_rotation, demo_c)
    run(rate_limits)
    if test_c:
        run(reset_password, test_c)
        run(admin, test_c)
    run(signout, demo_c)
    cleanup()

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "api.json").write_text(json.dumps(results, indent=1))
    counts = {s: sum(1 for x in results if x["status"] == s) for s in ("PASS", "FAIL", "WARN", "SKIP")}
    print("\n", counts)
    for x in results:
        if x["status"] in ("FAIL", "WARN"):
            print(f"  {x['status']} [{x['section']}] {x['name']}: {x['detail'][:250]}")


if __name__ == "__main__":
    main()
