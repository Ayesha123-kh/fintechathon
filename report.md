# Paisave: user-perspective test report

**Date:** 20 October 2026 · **Branch:** `osama-ui` at `156122c` · **Tested:** the local Docker Compose stack (web app
on :3000), which serves this commit (checked against the markup of the last change it ships).

## Verdict

The app works end to end from a user's point of view. Sign-up with an emailed code, sign-in, the dashboard and its
numbers, goal and bank details, the phone layout, the assistant chat (answers grounded in the person's own data, and
real changes made by chatting), voice notes in English and Urdu, the idle lock, fingerprint / face sign-in, password
reset, the admin console and offline mode all behave as intended. Every cross-account privacy check held.

Testing found **3 medium and 8 low issues, none blocking**, plus one documented limitation of the local stack. The
ones a user would notice first:

1. The assistant and the dashboard give **different figures for "this month's" spending** (Rs. 28,480 vs Rs. 16,374
   on food for the demo account).
2. The **deals pipeline has not produced a single deal**. All 12 deals on screen are demo seed data and expire on
   3 December, after which "Deals for your cards" will be empty.
3. **New sign-ups don't land in the onboarding chat** as the code intends. They see the dashboard instead.

## Results at a glance

| Layer | What it covers | Result |
|---|---|---|
| Code health | 74 backend unit tests (pytest), ruff, `tsc --noEmit`, ESLint | all clean |
| Scripted API journeys | 139 checks of sign-up, sign-in, every read, privacy, settings, voice, chat, idle lock, refresh, rate limits, reset, admin, sign-out, all through the web proxy | 135 pass · 4 warn |
| Changing things by chat | ask the live assistant to create a goal, then cancel it; verify both in the app | 7 / 7 pass |
| Bank-alert email parsing | every template the app's test-alert generator produces, OTP and promo emails, 4 free-form alerts | 5 pass · 2 warn |
| Browser journeys | 161 checks in headless Chrome 155, laptop (1440 px) and phone (390 / 320 px) | 154 pass · 4 warn · 2 fail · 1 info |

In total that's **314 automated checks: 301 pass, 10 warn, 2 fail**. Every warning and failure is listed under
Findings; none of them is a test artefact.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | Medium | The assistant and the dashboard disagree on "this month" |
| 2 | Medium | The deals desk has saved no deals; everything shown is seed data ending 3 Dec |
| 3 | Medium | New sign-ups don't land in the onboarding chat |
| 4 | Low | The chat stays locked for 2 minutes after an advisor turn that ends without a message |
| 5 | Low | Alerts that say "Avl Bal" or "new balance is" don't update the account balance |
| 6 | Low | If the session check can't reach the server, the app looks signed out |
| 7 | Low | Oversized uploads come back as a broken connection through the web proxy |
| 8 | Low | No confirmation after resetting a password |
| 9 | Low | Accessibility: deal badges are slightly under AA contrast; two scroll areas aren't keyboard-reachable |
| 10 | Low | Replaying an already-used refresh token doesn't end the session |
| 11 | Low | Demo data shows the JazzCash wallet at Rs. -1,498 |
| 12 | Info | In the local stack, per-address rate limits see the frontend container, not the visitor |

### 1. The assistant and the dashboard disagree on "this month" (medium)

- **What a user sees:** the dashboard's *Spending this month* shows Food & Dining at **Rs. 16,374**. Asking the
  assistant "How much did I spend on food this month?" gets "Is mahine tumne Food par **Rs. 28,480** kharch kiye."
- **Evidence:** in the database, the demo's food spending since 1 October (Pakistan time) is 16,374, and over the
  last 30 days it is 28,480.
- **Cause:** for this question the bot called `spending_summary`, which only takes a rolling `days` window
  (default 30): [backend/app/mcp/user_server.py:505](backend/app/mcp/user_server.py#L505). The dashboard and
  `get_overview` use the calendar month (`clock.month_start()`).
- **Fix:** give `spending_summary` a calendar-month option (for example `period: "this_month" | "last_30_days"`,
  defaulting to this month), or say in its docstring that "this month" questions should use `get_overview`.

### 2. The deals desk has saved no deals (medium)

- **What a user sees:** *Deals for your cards* always lists the same 12 deals, all ending 3 December. After that
  date the section will be empty.
- **Evidence:** all 12 rows in `deals` carry the demo seed's timestamp (19 Oct 15:38:01). None has been added in
  the roughly 17 hours since, although the Source Scout runs every 2 hours and the Crawler every 3 hours
  ([backend/app/worker.py:38-39](backend/app/worker.py#L38-L39)). The worker and gateway themselves are running:
  watchers have saved 34 signals (newest at 11:43 PKT today, matching the PSX schedule), researchers have saved
  8 notes, and merchant screening leaves nothing stuck in `screening`.
- **Cause:** not determined; the container logs aren't readable from the test session. The likeliest suspect is
  that `LLM_SUPPORTS_VISION` / `DESK_LLM_SUPPORTS_VISION` are true while the model server on :8001 reports
  `vision: false`, so the deal bots get a browser they can't use. The browser tool selector `mcp:browser:*`
  ([ai-ml/gateway/teams.py:35](ai-ml/gateway/teams.py#L35)) has also never been verified against OpenMausBot's real
  tool names.
- **Next step:** `docker compose logs omb` around 20 minutes past every third hour (the crawler's slot), and check
  one Deals Crawler turn in OpenMausBot.

### 3. New sign-ups don't land in the onboarding chat (medium)

- **What a user sees:** after entering the code, the dashboard opens with the chat closed. The sign-up page means
  to open it (`/dashboard?chat=1`) so the Finance Assistant can lead onboarding. People still see the "Step 1:
  connect your Gmail" banner, so they aren't stuck.
- **Evidence:** in every run the browser's only navigations were `/signup → /dashboard`, and the chat was closed
  5 seconds later.
- **Cause:** `verify()` in [frontend/src/app/signup/page.tsx:74-82](frontend/src/app/signup/page.tsx#L74-L82) calls
  `setUser()` first, which makes the session active while the page is still on `/signup`. The route guard
  ([frontend/src/lib/session.tsx:104](frontend/src/lib/session.tsx#L104)) then sends a signed-in person on a public
  page to `/dashboard`. The page's own `router.replace("/dashboard?chat=1")` only runs after `await reload()`, and
  is lost.
- **Fix:** let the guard send a just-created account to `/dashboard?chat=1`, or have the chat open by itself while
  `onboarding_completed` is false.

### 4. The chat stays locked after an advisor turn that ends without a message (low)

- **What a user sees:** the message box is disabled with "Savings Coach is typing…" for 2 minutes. Then it shows
  "Your assistant is taking longer than usual. You'll get a notification when it replies", although nothing is
  coming.
- **Evidence:** replaying exactly two live events on the person's chat channel (an advisor's `thinking`, then
  `idle` with no message) left the input locked; it unlocked only after about 120 seconds, with that error. This
  wasn't seen with live traffic during testing: normal turns end with a final message, which unlocks the input.
- **Cause:** in [frontend/src/components/ChatWidget.tsx:139-144](frontend/src/components/ChatWidget.tsx#L139-L144)
  any non-idle activity locks the input, `idle` only clears the activity, and only a final message unlocks it. The
  backend drops bot messages that are empty or not text
  ([backend/app/api/internal.py:57](backend/app/api/internal.py#L57)), so a turn that ends without text never sends
  the unlocking message.
- **Fix:** on `idle`, also clear `waiting` unless the person's own last message is still unanswered.

### 5. Alerts that say "Avl Bal" or "new balance is" don't update the balance (low)

- **What a user sees:** the transaction is recorded with the right amount and merchant, but the account balance
  doesn't follow the alert.
- **Evidence:** "…Avl Bal: PKR 45,210.33" and "…Your new balance is Rs. 3,250.00" both parse with
  `balance_after = None`. All 16 generated templates, plus "Available Balance", "Avail Bal" and "Current balance",
  are fine.
- **Cause:** `_BAL` in [backend/app/services/gmail.py:139](backend/app/services/gmail.py#L139) only knows
  *avail…, available, current, remaining* followed by *bal…*.
- **Fix:** tested against 8 phrasings with no regressions:
  `(?:avail\w*|avl\.?|available|current|remaining|new|account)\s*(?:bal\w*|limit)[^\d]{0,20}?` + `AMOUNT`.

### 6. If the session check can't reach the server, the app looks signed out (low)

- **What a user sees:** when the page loads but `/api/auth/session` fails (flaky network, backend restarting), the
  app shows the sign-in page as if the person had been signed out. Fully offline, it correctly shows the
  "You're offline" page.
- **Cause:** `reload()` treats any error as "signed out":
  [frontend/src/lib/session.tsx:50](frontend/src/lib/session.tsx#L50).
- **Fix:** on a network error, show a "can't reach Paisave, try again" state (or the offline page), and treat only an
  answer of `state: none` as signed out.

### 7. Oversized uploads come back as a broken connection through the web proxy (low)

- **What a user sees:** "Network problem" instead of "too large". This only happens if the app's own limits are
  bypassed (it shrinks photos to 256 px and stops recording at 30 s), so it's rare.
- **Evidence:** a 600 KB photo sent straight to the backend got a clean `413` 5 times out of 5. Through :3000, 2 to
  4 out of 5 attempts (varying by run) ended in a broken connection, and a 1.2 MB voice note once got a `500`.
  Small JSON bodies over the 64 KB cap are fine.
- **Cause:** `BodyLimit` ([backend/app/core/middleware.py:24](backend/app/core/middleware.py#L24)) answers `413` from
  `Content-Length` before reading the body and the connection closes, while Next's rewrite proxy is still sending
  the upload and loses the answer.
- **Fix:** read and discard the body (up to a hard ceiling) before answering, or check the size in Next as well.

### 8. No confirmation after resetting a password (low)

After saving a new password the app goes to `/signin?reset=1`
([frontend/src/app/forgot-password/page.tsx:66](frontend/src/app/forgot-password/page.tsx#L66)), but the sign-in page
never reads `reset`, so nothing says the change worked. A one-line notice ("Password changed. Sign in with your new
password.") would close the loop.

### 9. Accessibility (low)

An axe-core scan of the landing page, sign-in, sign-up, dashboard and chat found no critical issues and two serious
ones:

- White text on the deal badges (`--deal: #c5583d`,
  [frontend/src/app/globals.css:30](frontend/src/app/globals.css#L30)) has a contrast ratio of **4.34:1**, just under
  AA's 4.5:1. A slightly darker shade fixes it. This affects the landing page, dashboard and chat.
- The bank / transaction list and the chat's message list scroll but can't be reached by keyboard. Adding
  `tabIndex={0}` and an `aria-label` fixes it.

Sign-in and sign-up are clean.

### 10. Replaying an already-used refresh token doesn't end the session (low, hardening)

An old refresh token is correctly refused, but the session stays valid. Seeing a used token again is the usual sign
that it was stolen, so `rotate_refresh` ([backend/app/core/security.py:112](backend/app/core/security.py#L112)) could
keep the previous hash and revoke the session when that hash comes back.

### 11. Demo data shows the JazzCash wallet at Rs. -1,498 (low, cosmetic)

The demo seed ([backend/alembic/versions/0002_demo_data.py:136](backend/alembic/versions/0002_demo_data.py#L136))
lets the wallet's debits outrun its top-ups, so the dashboard and bank details show **Rs. -1,498**, which looks like a
bug in a demo. `rs()` also writes negatives as "Rs. -1,498", while the activity list uses "− Rs. 1,787". Either raise
the seed's monthly top-up or clamp the wallet, and format negatives the same way everywhere
([frontend/src/lib/api.ts:105](frontend/src/lib/api.ts#L105)).

### 12. Local stack: per-address rate limits see the frontend container (info, documented)

Next.js forwards a client's own `X-Forwarded-For` unchanged and doesn't add one, and the backend takes the right-most
entry ([backend/app/core/deps.py:27](backend/app/core/deps.py#L27), `TRUSTED_PROXY_HOPS=1`). Locally every browser
therefore appears as `172.18.0.5` and shares the per-address limits: 10 sign-ups an hour, 5 reset emails an hour and
300 anonymous API calls a minute, for everyone together. A client can also pick its own address by sending the
header. This is already noted in [backend/app/core/config.py:33-37](backend/app/core/config.py#L33-L37): on Railway
the edge appends the real address, and the per-account limits don't depend on it. It's only worth remembering if
the compose stack is ever used for a busy public demo.

## What was verified

- **Landing page:** loads in about 0.65 s and explains the product. Sign up and Sign in work, there are no broken
  images and no sideways scrolling at 1440, 390 or 320 px.
- **Sign-up:** rejects short passwords, invalid emails and taken addresses. The emailed 6-digit code is required,
  can't be resent within 60 s, rejects a wrong code and works only once. Nothing touches the database before the
  code is entered. Cookies are HttpOnly and SameSite=Lax, with the refresh cookie limited to `/api/auth`. A private
  assistant team (Finance Assistant, Savings Coach, Deals Advisor; no investment bot without opt-in) is provisioned
  in the background.
- **A new user's first visit:** empty dashboard with zero totals and helpful empty states. Chat is gated until Gmail
  is connected (`409 connect_gmail_first`). "Connect Gmail" produces a Google consent URL with read-only scope.
- **Sign-in:** a wrong password shows "That email and password don't match." Unknown emails get the same answer.
  Email is case-insensitive. The 9th wrong attempt in 15 minutes is blocked with `Retry-After`. Sign-in reaches the
  dashboard in about 1.7 s.
- **Forgot password:** the same "sent" answer for unknown emails. The link opens "Choose a new password",
  mismatches are caught, bogus or reused links are refused, the reset signs out every device, the old password
  stops working and the new one works.
- **Dashboard numbers reconcile:** total balance = sum of banks (Rs. 424,951), spendable = balance − savings,
  spent this month = the category breakdown, progress between 0 and 1, monthly cards present. Bank and goal names
  appear on screen, with no NaN, undefined or [object Object] anywhere.
- **Goal details:** remaining, monthly need, recent pace and projected date are consistent (for example Umrah:
  532,840 left ÷ 5 months = 106,568 a month; at 16,887 a month it lands around June 2029, shown as "a little behind
  schedule"). An unknown goal shows "This goal could not be found."
- **Bank details:** the modal shows balance, cards and transactions, doesn't make the page jump, and closes with
  Escape.
- **Settings:** Gmail connection, fingerprint / face, appearance and sign-out. Name and language changes save, and
  an unsupported language is ignored. Profile photo upload, display (private cache) and removal work; disguised
  non-images and photos over 512 KB are refused. Dark mode switches the whole app.
- **Phone:** the bottom bar reads Goals · Spending · Home · Deals · Activity, each tab opens its own page with
  content and is highlighted, with no sideways scrolling. Chat opens full-screen.
- **Chat:**
  - The live stream connects, and the person counts as online, so there are no duplicate pushes.
  - Messages appear at once, and the input locks while the assistant works, with live "thinking / tool" progress.
  - Replies arrived in 3 to 36 s, in Roman Urdu as set in the profile, and matched the data: the exact goal list
    with 11 / 7 / 31 %, "3 active savings goals (1 completed)", and a total balance of Rs. 424,951.
  - History is saved, opening the chat clears the unread badge, and empty or over-4,000-character messages are
    refused. The member key never leaks.
- **Changing things by chat:** "Create a goal E2E Bicycle, Rs 40,000 by 30 June 2027" called `create_goal` in 8 s,
  and the goal appeared on the Goals screen and dashboard with the right target, deadline and Rs. 4,444 a month.
  "Cancel it" called `update_goal` in 12 s and the goal disappeared.
- **Voice notes:**
  - An English note came back as "How much did I spend on food this month? And can I still save twenty thousand
    rupees?" in 2.2 s.
  - An Urdu note came back in Urdu script when the profile language is Urdu.
  - In the browser, the real microphone path (Chrome's fake mic) put the text in the message box for editing and
    didn't send it.
  - Non-WAV audio, notes under 0.3 s and notes over 30 s are refused.
- **Privacy and security:** writes without the CSRF header are refused, private data needs a session, and another
  account's goals, transactions and chat are invisible. Regular users can't use admin endpoints. Gateway endpoints
  need the internal key, `/mcp` isn't reachable through the web app, and responses carry security headers and
  `no-store`.
- **Idle lock:** after 5 idle minutes every private call answers `423`, including the live stream and token
  refresh. The app shows the lock screen (never on the landing page). A wrong password doesn't unlock; the right
  one returns straight to the dashboard.
- **Fingerprint / face (passkeys, via Chrome's virtual authenticator):** turning it on in Settings registers a
  passkey, a locked app unlocks with it without typing anything, and "Fingerprint or face" on the sign-in page signs
  in without email or password.
- **Admin:**
  - All 12 admin APIs and 10 admin pages load with data, and user counts exclude admins.
  - Search finds a user. Disabling an account signs it out at once and blocks sign-in, and re-enabling restores it.
  - Actions are written to the audit log. Deleting an account also removes its assistant team, and admins can't
    delete themselves.
  - Admins can't open the personal dashboard, and users can't open the admin console.
- **PWA:** the manifest and every icon load, the service worker is registered and never caches `/api`, and fully
  offline the app shows "You're offline. Your savings are safe."
- **Bank-alert parsing:** all 16 generated templates give the right amount, direction, merchant, balance and account
  digits. OTP and promotional emails are not recorded, and Meezan-style credit and ATM withdrawal alerts are
  understood.
- **Background work:** the worker's hourly and daily jobs are visibly running (signals, research notes, merchant
  screening). The deals desk is the exception (finding 2).

## Not covered

- **Connecting a real Gmail inbox and syncing it.** Google's consent screen can't be automated here. The consent URL,
  its scope and the parser were tested instead.
- **Web-push delivery to a real device**, and the Investment Advisor opt-in with its market features.
- **Weekly and monthly scheduled nudges** (Friday motivation, Sunday review, sadqah reminders, month-end sweep):
  none was due during testing.
- **Real phones and iOS Safari.** Phones were emulated in Chrome at 390 and 320 px.
- **Production settings** (Railway, HTTPS cookies, real proxy hops) and load testing.

## Effects on the dev environment

- **Emails:** none were sent. The two calls that email someone (sign-up code, reset link) went to a second backend
  on :8010 with SMTP switched off, which writes the email to its log. It shares the stack's Postgres and Dragonfly,
  and was stopped afterwards.
- **Throwaway accounts:** `e2e-*@example.com` users were created and then deleted through the admin console,
  together with their assistant teams. The gateway is back to 3 rooms and 40 bots.
- **Demo account:** a few test questions and answers are now in its chat history, plus one cancelled goal
  ("E2E Bicycle", hidden in the app). A test passkey was added and removed again.
- **Rate limits:** the counters these tests drive up (demo and admin sign-ins, sign-up and reset counters) were
  reset in Dragonfly between runs.
- **Teammates' accounts:** the two teammates' accounts in the dev database were not touched.

## How it was tested, and how to re-run it

The suites are in [e2e/](e2e/). Setup, once, from the repo root:

```bash
(cd backend && UV_PROJECT_ENVIRONMENT=../e2e/venv uv sync --frozen)
(cd e2e/browser && npm i)
```

Then, with the compose stack and the model servers running, run `e2e/run_all.sh`. It takes about 15 minutes, writes
JSON results and a per-check table to `e2e/results/`, and saves screenshots to `e2e/shots/`. The suites run one
after another because they share the demo account's chat.

| File | What it does |
|---|---|
| `api_e2e.py` | API journeys through the web proxy, as a browser would make them |
| `chat_actions.py` | create and cancel a goal by chatting, checked against the app |
| `ingest_check.py` | bank-alert parsing through `parse_email` (regex first, then the live model) |
| `browser/e2e.js` | headless-Chrome journeys and the axe-core scan |
| `housekeeping.py` | deletes `e2e-*` users and resets the suite's own rate-limit counters |

A few techniques worth knowing:

- **Idle lock:** simulated by deleting the session's `sess:<sid>:active` key, which is exactly what 5 idle minutes
  do on the server.
- **Passkeys:** use Chrome's virtual authenticator.
- **Voice:** Chrome's fake microphone plays `e2e/fixtures/english.wav`.
- **Live model:** chat answers come from Qwen3.5-9B on llama.cpp; speech-to-text from Qwen3-ASR.

Two apparent failures during development turned out to be test bugs and were fixed before the final pass:

- A check that waited for the chat's Send button never resolved, because the app shows the mic button when the box
  is empty.
- A crash came from clicking an element the app hides at that screen width.

## Appendix: every check

### Scripted API journeys · 135 pass, 4 warn

<details><summary><b>Platform, proxy and security basics</b> (8/8 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Health check through the web proxy |  |
| ✅ | API responses carry security headers and no-store |  |
| ✅ | Writes without the CSRF header are refused (403) |  |
| ✅ | Private data needs a session (401 when signed out) |  |
| ✅ | Gateway-only endpoints refuse calls without the internal key |  |
| ✅ | Bot tool servers (/mcp) are not reachable through the web proxy |  |
| ✅ | Oversized request bodies are refused (413) |  |
| ✅ | Web-push public key is published |  |

</details>

<details><summary><b>Every screen answers over HTTP</b> (6/6 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | 20 app pages return 200 HTML |  |
| ✅ | Unknown pages return 404 |  |
| ✅ | PWA manifest is served with a start URL and icons |  |
| ✅ | Every manifest icon loads |  |
| ✅ | Service worker script is served |  |
| ✅ | Service worker never caches /api |  |

</details>

<details><summary><b>Sign-up with an emailed code (new user)</b> (12/12 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | A password under 8 characters is rejected |  |
| ✅ | An invalid email is rejected |  |
| ✅ | An email that already has an account is refused (409 email_taken) |  |
| ✅ | Sign-up step 1 accepts the details and says a code was sent |  |
| ✅ | A 6-digit code email is produced for the (lower-cased) address |  |
| ✅ | Nothing is written to the database before the code is entered |  |
| ✅ | Asking for a new code within 60 s is refused (429) |  |
| ✅ | A wrong code is rejected (400 invalid_code) |  |
| ✅ | The right code creates the account and signs the person in |  |
| ✅ | The name is trimmed and onboarding starts as not done |  |
| ✅ | The same code can't be used twice |  |
| ✅ | Session cookies are HttpOnly, SameSite=Lax; refresh cookie limited to /api/auth |  |

</details>

<details><summary><b>Returning user: sign-in and every dashboard read (demo account)</b> (31/33 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | A wrong password is refused (401 invalid_credentials) |  |
| ✅ | An unknown email gets the same answer (no account discovery) |  |
| ✅ | Sign-in works (email is case-insensitive) |  |
| ⚠️ | Per-address rate limits see the caller's own address through the web proxy | backend saw ['172.18.0.5'] (the frontend container), so every browser shares one bucket in the local stack |
| ⚠️ | A client can't choose its own rate-limit address with X-Forwarded-For | the local stack trusts a client-sent X-Forwarded-For (documented in config.py; Railway's edge appends) |
| ✅ | Profile: onboarded, assistant ready |  |
| ✅ | Dashboard loads |  |
| ✅ | Total balance equals the sum of bank balances |  |
| ✅ | Spendable = balance − savings (never negative) |  |
| ✅ | Spent this month equals the category breakdown |  |
| ✅ | Monthly cards are present (saved this month, deal savings this month, salary flag) |  |
| ✅ | Goal progress is between 0 and 1 |  |
| ✅ | No bank shows negative savings or spendable |  |
| ✅ | Deals for you are listed |  |
| ✅ | Goal list loads |  |
| ✅ | Goal details load with history, monthly rate and projection |  |
| ✅ | Goal remaining = target − saved |  |
| ✅ | An unknown goal id is a 404 |  |
| ✅ | A malformed goal id is rejected cleanly (422, not 500) |  |
| ✅ | Bank details load with accounts, cards and recent transactions |  |
| ✅ | Activity: 90 days of transactions load |  |
| ✅ | Every transaction has an amount, a direction and a title |  |
| ✅ | Huge page sizes are capped (≤200) |  |
| ✅ | Deals list loads |  |
| ✅ | Deal search with no match returns an empty list |  |
| ✅ | Notifications load |  |
| ✅ | GET /api/chat/unread |  |
| ✅ | GET /api/chat/messages |  |
| ✅ | GET /api/chat/status |  |
| ✅ | GET /api/auth/webauthn/credentials |  |
| ✅ | GET /api/email/connections |  |
| ✅ | Chat history pages (limit respected, oldest first) |  |
| ✅ | Loading older chat messages works |  |

</details>

<details><summary><b>A brand-new user's first visit</b> (10/10 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Session reports active with a 5-minute idle lock |  |
| ✅ | Profile loads (language en, not onboarded) | 200 None |
| ✅ | Empty dashboard loads with zero totals and no errors |  |
| ✅ | Empty goal list, bank details and activity load |  |
| ✅ | Email settings say Gmail is configured and nothing is connected |  |
| ✅ | 'Connect Gmail' produces a Google consent URL with read-only Gmail scope |  |
| ✅ | Chat is gated until Gmail is connected (409 connect_gmail_first) |  |
| ✅ | The private assistant team gets provisioned (status ready) |  |
| ✅ | New users get Finance Assistant, Savings Coach and Deals Advisor (no investment bot unless opted in) |  |
| ✅ | Test-alert tool refuses politely without a connected inbox |  |

</details>

<details><summary><b>Privacy between accounts (row-level security)</b> (4/4 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Another user's goal can't be opened by id (404) |  |
| ✅ | Another user's transactions don't appear |  |
| ✅ | Another user's chat history doesn't appear |  |
| ✅ | A regular user can't use admin endpoints (403 admin_only) |  |

</details>

<details><summary><b>Settings: name, language and profile photo (new user)</b> (7/8 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Name and language can be changed |  |
| ✅ | An unsupported language is ignored |  |
| ✅ | A photo can be uploaded |  |
| ✅ | The photo is served back as an image, cacheable for the owner only |  |
| ✅ | A non-image disguised as .png is refused (415) |  |
| ✅ | A photo over 512 KB is refused by the server (413) |  |
| ⚠️ | …and that 413 reaches the browser intact through the web proxy | 5 tries via :3000 -> ['RemoteProtocolError', '413', '413', '413', 'RemoteProtocolError'] |
| ✅ | The photo can be removed |  |

</details>

<details><summary><b>Voice notes to editable text</b> (6/6 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | An English voice note becomes text | 200 None 'How much did I spend on food this month? And can I still save twenty thousand rupees?' |
| ✅ | …in Latin script when the language is English |  |
| ✅ | An Urdu voice note comes back in Urdu script when the language is Urdu | 'میں یہ بتاؤں کہ میں سرمایہ کاری کرنا چاہتا ہوں، یہ پیسے جو سیوینس میں ہیں، تمھارا کیا خیال ہے، مجھے کیس طرف جانا چاہیے؟ ویسے تو میں گولڈ کا سوچ رہا تھا۔' |
| ✅ | Non-WAV audio is refused (415) |  |
| ✅ | A note under 0.3 s is refused (422 audio_too_short) |  |
| ✅ | A note over 30 s is refused (413) |  |

</details>

<details><summary><b>Chat with the assistant team (demo account, live model)</b> (12/12 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Live chat stream connects (text/event-stream) |  |
| ✅ | While the stream is open the person counts as online (no duplicate pushes) |  |
| ✅ | Sending a message is accepted and echoed |  |
| ✅ | The sent message appears on the live stream |  |
| ✅ | Live progress (thinking / tool / writing) is streamed while the bot works |  |
| ✅ | A final bot reply arrives | 3s from Finance Assistant: 'Tumhare paas abhi **3 active savings goals** hain (1 completed). 📊' |
| ✅ | The reply uses the person's real data (3 active goals) | Tumhare paas abhi **3 active savings goals** hain (1 completed). 📊 |
| ✅ | The reply never leaks the room's member key |  |
| ✅ | Question and reply are saved in chat history |  |
| ✅ | Opening the chat clears the unread badge |  |
| ✅ | Messages over 4000 characters are refused (422) |  |
| ✅ | Empty messages are refused (422) |  |

</details>

<details><summary><b>Idle lock after 5 minutes, unlock with password</b> (7/7 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | After 5 idle minutes private data answers 423 locked |  |
| ✅ | The app's launch check reports 'locked' |  |
| ✅ | A locked session can't be refreshed around the lock |  |
| ✅ | The live chat stream is locked too |  |
| ✅ | Unlock with a wrong password is refused |  |
| ✅ | Unlock with the right password works |  |
| ✅ | Data loads again after unlocking |  |

</details>

<details><summary><b>Staying signed in: access-token refresh</b> (3/4 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Refresh issues a new access token and rotates the refresh token |  |
| ✅ | An old (already used) refresh token is refused |  |
| ⚠️ | Replaying a stolen refresh token also ends the session (theft detection) | session still works after replay: /api/me=200 |
| ✅ | An expired access token is renewed silently from the current refresh cookie |  |

</details>

<details><summary><b>Brute-force protection</b> (2/2 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | The 9th wrong password in 15 minutes is blocked (429) |  |
| ✅ | Blocked responses say when to retry (Retry-After) |  |

</details>

<details><summary><b>Forgot password (new user)</b> (9/9 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Unknown emails get the same 'sent' answer (no account discovery) |  |
| ✅ | A reset email with a link to the app is produced |  |
| ✅ | A bogus reset link is refused |  |
| ✅ | A too-short new password is refused |  |
| ✅ | The reset link sets a new password |  |
| ✅ | Resetting signs out every existing session |  |
| ✅ | A reset link works only once |  |
| ✅ | The old password no longer works |  |
| ✅ | The new password works |  |

</details>

<details><summary><b>Admin console</b> (15/15 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Admin can sign in |  |
| ✅ | Admins have no personal finance area (403 admin_account) |  |
| ✅ | Admins have no assistant chat (403) |  |
| ✅ | All 12 admin views load |  |
| ✅ | User counts exclude admin accounts |  |
| ✅ | The new sign-up shows up in the user list with its assistant status |  |
| ✅ | User search finds them |  |
| ✅ | Admin can disable an account |  |
| ✅ | Disabling signs the person out at once |  |
| ✅ | A disabled account can't sign in (403 account_disabled) |  |
| ✅ | Re-enabled account can sign in again |  |
| ✅ | Admin actions are written to the audit log |  |
| ✅ | Admin can delete an account (and its assistant team) |  |
| ✅ | A deleted account can't sign in |  |
| ✅ | Admins can't delete themselves / admin accounts |  |

</details>

<details><summary><b>Sign out</b> (3/3 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Sign out succeeds and clears cookies |  |
| ✅ | After sign-out private data is refused |  |
| ✅ | After sign-out the app's launch check says 'none' |  |

</details>


### Changing things by chatting · 7 pass

<details><summary><b>Changing things by chatting (demo account, live model)</b> (7/7 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Demo signs in |  |
| ✅ | Assistant replied to the create request (8 s) | 8s tools=['fin_user_create_goal']: '✅ **Goal created successfully!**  **E2E Bicycle:** - Target: Rs. 40,000 - Deadline: 30 June 2027 - Monthly needed: Rs. 4,444 |
| ✅ | The goal really exists afterwards (Goals screen) |  |
| ✅ | …with the target and deadline that were asked for |  |
| ✅ | …and it shows on the dashboard |  |
| ✅ | Assistant replied to the cancel request (12 s) | 12s tools=['agents_session_search', 'fin_user_get_overview', 'fin_user_update_goal']: "✅ **Goal 'E2E Bicycle' cancel ho gaya!** 🚲❌  Ab tumhare paas **3 active s |
| ✅ | The cancelled goal is gone from the Goals screen |  |

</details>


### Bank-alert email parsing · 5 pass, 2 warn

<details><summary><b>Bank-alert email parsing</b> (5/7 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | All 16 test-alert templates parse to the right amount, direction, merchant, balance and account |  |
| ✅ | OTP emails are never turned into transactions |  |
| ⚠️ | Free-form alert 'Debit card purchase' is understood | wanted {'amount': 2450.0, 'direction': 'debit', 'merchant': 'foodpanda', 'balance_after': 45210.33}, got {'is_transaction': True, 'amount': 2450.0, 'direction': |
| ⚠️ | Free-form alert 'JazzCash' is understood | wanted {'amount': 1500.0, 'direction': 'debit', 'merchant': 'ali', 'balance_after': 3250.0}, got {'is_transaction': True, 'amount': 1500.0, 'direction': 'debit' |
| ✅ | Free-form alert 'Meezan Bank Credit Alert' is understood |  |
| ✅ | Free-form alert 'Cash Withdrawal Alert' is understood |  |
| ✅ | Promotional emails aren't recorded as spending |  |

</details>


### Browser journeys (headless Chrome) · 154 pass, 4 warn, 2 fail, 1 info

<details><summary><b>landing</b> (13/13 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | laptop: landing page loads (645 ms) | Paisave · your savings assistant for Pakistan |
| ✅ | laptop landing: no sideways scrolling |  |
| ✅ | Landing explains the product (How it works, chat, deals) |  |
| ✅ | Landing offers Sign up and Sign in |  |
| ✅ | No broken images on the landing page |  |
| ✅ | 'Sign up' leads to the sign-up form |  |
| ✅ | laptop landing: no JS errors, failed requests or 5xx |  |
| ✅ | phone: landing page loads (647 ms) | Paisave · your savings assistant for Pakistan |
| ✅ | phone landing: no sideways scrolling |  |
| ✅ | phone landing: no JS errors, failed requests or 5xx |  |
| ✅ | small phone: landing page loads (656 ms) | Paisave · your savings assistant for Pakistan |
| ✅ | small phone landing: no sideways scrolling |  |
| ✅ | small phone landing: no JS errors, failed requests or 5xx |  |

</details>

<details><summary><b>guards</b> (7/7 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Signed out, /dashboard sends you to sign in |  |
| ✅ | Signed out, /goals sends you to sign in |  |
| ✅ | Signed out, /activity sends you to sign in |  |
| ✅ | Signed out, /admin sends you to sign in |  |
| ✅ | A wrong password shows a readable error and stays on sign in |  |
| ✅ | Sign in links to 'Forgot password' |  |
| ✅ | sign-in page: no JS errors, failed requests or 5xx |  |

</details>

<details><summary><b>signup</b> (16/17 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | A short password is caught before sending |  |
| ✅ | After 'Continue' the app asks for the emailed 6-digit code |  |
| ✅ | The code screen names the address |  |
| ✅ | The verification email was produced |  |
| ✅ | The right code creates the account and opens the dashboard |  |
| ✅ | New users land with the chat open, asked to connect Gmail first |  |
| ✅ | new user's dashboard: no NaN / undefined / [object Object] on screen |  |
| ✅ | sign-up flow: no JS errors, failed requests or 5xx |  |
| ✅ | 'Forgot password' confirms a link is on its way |  |
| ✅ | The reset email was produced with a link back to the app |  |
| ✅ | The link opens 'Choose a new password' |  |
| ✅ | Mismatched passwords are caught |  |
| ✅ | Saving the new password returns to sign in |  |
| ⚠️ | Sign in confirms the password was changed | Paisave Welcome back  Sign in to see your savings and goals.  Email Password Forgot password? Sign in or Fingerprint or face  New here? Create an account |
| ✅ | The new password signs in |  |
| ✅ | The reset signed out the other browser |  |
| ✅ | password reset flow: no JS errors, failed requests or 5xx |  |

</details>

<details><summary><b>signupchat</b> (0/1 passed)</summary>

| | Check | Detail |
|---|---|---|
| ❌ | After sign-up the dashboard opens with the chat open (?chat=1) | chat open=false; client-side URL changes: ["/signup","/dashboard"]; final /dashboard |

</details>

<details><summary><b>dashboard</b> (27/27 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Demo signs in and lands on the dashboard (1662 ms) | http://localhost:3000/dashboard |
| ✅ | Dashboard shows Home, Goals, Spending, Banks and Deals |  |
| ✅ | Bank names from the account appear on screen |  |
| ✅ | Active goal names appear on screen |  |
| ✅ | Monthly cards are labelled per month, not per week |  |
| ✅ | dashboard: no NaN / undefined / [object Object] on screen |  |
| ✅ | dashboard: no sideways scrolling |  |
| ✅ | dashboard: no JS errors, failed requests or 5xx |  |
| ✅ | Goals link to their detail page |  |
| ✅ | Goal details show the name, progress and history |  |
| ✅ | goal details: no NaN / undefined / [object Object] on screen |  |
| ✅ | goal details: no JS errors, failed requests or 5xx |  |
| ✅ | An unknown goal shows a friendly not-found message |  |
| ✅ | Tapping a bank opens its details |  |
| ✅ | Bank details list balance, cards and recent transactions |  |
| ✅ | The page behind doesn't jump when the bank modal opens |  |
| ✅ | Escape closes the bank details |  |
| ✅ | Settings open from the avatar |  |
| ✅ | Settings offer Gmail connection, fingerprint/face, appearance and sign out |  |
| ✅ | Dark mode switches the whole app |  |
| ✅ | …and back to light |  |
| ✅ | bank modal & settings: no JS errors, failed requests or 5xx |  |
| ✅ | The service worker is registered (installable, offline shell) |  |
| ✅ | Offline, the app shows its own offline page |  |
| ✅ | Signed in, /signin sends you to the dashboard |  |
| ✅ | A regular user can't open the admin console |  |
| ✅ | The landing page knows you're signed in (Dashboard button) |  |

</details>

<details><summary><b>chat</b> (12/12 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | The chat opens from the chat button |  |
| ✅ | Chat shows the advisors by name |  |
| ✅ | Earlier conversation is shown |  |
| ✅ | My message appears in the chat at once |  |
| ✅ | Input is locked while the assistant replies | textarea locked=true send disabled=null |
| ✅ | A typing / progress indicator shows while it works |  |
| ✅ | The assistant replies and the input unlocks (4 s) | 4s: 13:48  New messages  Finance Assistant  Tumhara total balance Rs. 424,951 hai across all banks (Meezan, HBL, JazzCash). 📊  13:48 |
| ✅ | The reply quotes the real total balance (Rs 424,951) | 13:48  New messages  Finance Assistant  Tumhara total balance Rs. 424,951 hai across all banks (Meezan, HBL, JazzCash). 📊  13:48 |
| ✅ | There is a voice-note button |  |
| ✅ | Recording starts (Stop button shown) |  |
| ✅ | The voice note becomes editable text in the message box (not sent automatically) | "How much did I spend on food this month, and can I still save twenty thousand rupees? How much did I spend on?" |
| ✅ | chat: no JS errors, failed requests or 5xx |  |

</details>

<details><summary><b>lock</b> (8/8 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | After 5 idle minutes the app shows the lock screen |  |
| ✅ | The landing page itself is never covered by the lock screen |  |
| ✅ | …but heading back into the app asks to unlock |  |
| ✅ | A wrong password doesn't unlock |  |
| ✅ | The right password unlocks straight back into the dashboard |  |
| ✅ | lock screen: no JS errors, failed requests or 5xx |  |
| ✅ | Sign out returns to sign in |  |
| ✅ | After sign out the dashboard is closed |  |

</details>

<details><summary><b>phone</b> (27/27 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | phone dashboard: no sideways scrolling |  |
| ✅ | Phone bottom bar has Goals · Spending · Home · Deals · Activity |  |
| ✅ | Phone: 'Goals' opens /goals with content |  |
| ✅ | phone Goals: no sideways scrolling |  |
| ✅ | phone Goals: no NaN / undefined / [object Object] on screen |  |
| ✅ | Phone: 'Goals' is highlighted in the bottom bar |  |
| ✅ | Phone: 'Spending' opens /spending with content |  |
| ✅ | phone Spending: no sideways scrolling |  |
| ✅ | phone Spending: no NaN / undefined / [object Object] on screen |  |
| ✅ | Phone: 'Spending' is highlighted in the bottom bar |  |
| ✅ | Phone: 'Home' opens /dashboard with content |  |
| ✅ | phone Home: no sideways scrolling |  |
| ✅ | phone Home: no NaN / undefined / [object Object] on screen |  |
| ✅ | Phone: 'Home' is highlighted in the bottom bar |  |
| ✅ | Phone: 'Deals' opens /deals with content |  |
| ✅ | phone Deals: no sideways scrolling |  |
| ✅ | phone Deals: no NaN / undefined / [object Object] on screen |  |
| ✅ | Phone: 'Deals' is highlighted in the bottom bar |  |
| ✅ | Phone: 'Activity' opens /activity with content |  |
| ✅ | phone Activity: no sideways scrolling |  |
| ✅ | phone Activity: no NaN / undefined / [object Object] on screen |  |
| ✅ | Phone: 'Activity' is highlighted in the bottom bar |  |
| ✅ | phone pages: no JS errors, failed requests or 5xx |  |
| ✅ | Phone: chat opens |  |
| ✅ | Phone: chat fills the screen |  |
| ✅ | phone settings: no sideways scrolling |  |
| ✅ | phone chat & settings: no JS errors, failed requests or 5xx |  |

</details>

<details><summary><b>admin</b> (33/33 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Admin signs in straight to the admin console |  |
| ✅ | /admin renders with data |  |
| ✅ | /admin: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/users renders with data |  |
| ✅ | /admin/users: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/users: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/agents renders with data |  |
| ✅ | /admin/agents: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/agents: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/plans renders with data |  |
| ✅ | /admin/plans: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/plans: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/deals renders with data |  |
| ✅ | /admin/deals: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/deals: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/companies renders with data |  |
| ✅ | /admin/companies: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/companies: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/banks renders with data |  |
| ✅ | /admin/banks: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/banks: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/cards renders with data |  |
| ✅ | /admin/cards: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/cards: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/assets renders with data |  |
| ✅ | /admin/assets: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/assets: no JS errors, failed requests or 5xx |  |
| ✅ | /admin/watchlists renders with data |  |
| ✅ | /admin/watchlists: no NaN / undefined / [object Object] on screen |  |
| ✅ | /admin/watchlists: no JS errors, failed requests or 5xx |  |
| ✅ | Admin user list shows the demo user but not admins |  |
| ✅ | Admins can't open the personal dashboard |  |

</details>

<details><summary><b>passkey</b> (7/7 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Settings offer to turn on fingerprint / face |  |
| ✅ | Turning it on registers a passkey for this device |  |
| ✅ | A locked app unlocks with fingerprint / face, no password typed |  |
| ✅ | Sign in offers 'Fingerprint or face' |  |
| ✅ | Fingerprint or face signs in without email or password |  |
| ✅ | passkeys: no JS errors, failed requests or 5xx |  |
| ✅ | Test passkey removed again afterwards |  |

</details>

<details><summary><b>a11y</b> (2/5 passed)</summary>

| | Check | Detail |
|---|---|---|
| ⚠️ | /: no critical / serious accessibility issues | color-contrast (serious) ×3: .gap-3\.5.p-3.rounded-2xl:nth-child(1) > .h-12.min-w-\[4\.75rem\].rounded-xl, .gap-3\.5.p-3.rounded-2xl:nth-child(2) > .h-12.min-w- |
| ✅ | /signin: no critical / serious accessibility issues |  |
| ✅ | /signup: no critical / serious accessibility issues |  |
| ⚠️ | /dashboard: no critical / serious accessibility issues | color-contrast (serious) ×6: .gap-3\.5.p-3[title="Any card or cash"]:nth-child(1) > .min-w-\[4\.75rem\].bg-deal.text-white, .gap-3\.5.p-3.bg-surface:nth-child(2 |
| ⚠️ | chat panel: no critical / serious accessibility issues | color-contrast (serious) ×6: .gap-3\.5.p-3[title="Any card or cash"]:nth-child(1) > .min-w-\[4\.75rem\].rounded-xl.bg-deal, .gap-3\.5.p-3.bg-surface:nth-child(2 |

</details>

<details><summary><b>chatidle</b> (2/4 passed)</summary>

| | Check | Detail |
|---|---|---|
| ✅ | Before: the input is free |  |
| ✅ | While an advisor is thinking, the input locks |  |
| ❌ | When that advisor finishes without a message, the input unlocks again | input still locked 3 s after the turn ended (idle) |
| ℹ️ | …it only unlocks via the silence fallback | after ~120 s, showing: taking longer than usual. You'll get a notification when it replies. |

</details>

