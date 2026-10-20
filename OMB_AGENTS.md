# OpenMausBot agents: triggers and routines

What wakes each agent, when, and what it does. "OMB" is OpenMausBot, the agent platform that runs the bots.

- All schedules run in **Asia/Karachi** time from the `worker` container: [backend/app/worker.py](backend/app/worker.py).
- Job bodies: [backend/app/services/jobs.py](backend/app/services/jobs.py).
- Agent catalog and tool allow-lists: [ai-ml/gateway/teams.py](ai-ml/gateway/teams.py). Prompts: `ai-ml/prompts/<agent>/SOUL.md`.
- Gateway (backend ↔ OMB bridge): [ai-ml/gateway/main.py](ai-ml/gateway/main.py).

## Overview

| Group | Agents | Talks to users? | Woken by |
|---|---|---|---|
| Shared desks | 29 (16 watchers, 5 researchers, 5 analysts, 3 deals bots) | No | The scheduler, on a timetable |
| Per-user teams | 3–4 per user (Finance Assistant, Savings Coach, Deals Advisor, Investment Advisor if opted in) | Yes, in a private room | A user message, or the Sunday check-in |
| Worker jobs | None, ordinary Python in the worker (two of them call the self-hosted model, see section 3) | Via notifications | The scheduler |

Shared desks write to the shared database (signals, research notes, deals). Each user's private advisors read from it through their own tools. A desk never sees user data, and a user's bots never see anyone else's.

**Which model runs what:** the per-user teams, merchant screening and bank-email parsing always use the self-hosted model (`LLM_*`), because they touch user data. The shared desks use it too unless `DESK_LLM_*` is set, in which case they run on that third-party OpenAI-compatible model.

## 1. Shared desks (scheduled)

The worker sends the bot a `[SCHEDULER] …` message through the gateway (`POST /bots/trigger`). A trigger wakes **every bot of that kind on that desk**. These bots run on the desk model: the third-party LLM when `DESK_LLM_BASE_URL` and `DESK_LLM_MODEL` are set (OMB instance `desk`), otherwise the self-hosted one.

| Agent | Schedule | What it does |
|---|---|---|
| **Watchers** (16 clusters: PSX 6, global stocks 3, real estate 3, bullion 2, crypto 2) | PSX: Mon–Fri hourly at :40, 09:40–15:40. Crypto: every hour at :05. Bullion: 10:15, 13:15, 16:15, 19:15. Global stocks: Mon–Fri 19:00 and 22:00. Real estate: daily 11:30 | Fetch fresh data for every symbol in the cluster's watchlist and emit **signals** only where something meaningful changed |
| **Researchers** (one per asset desk, 5) | 08:00 and 16:00 | Gather credible news and data and save a **research note**. Use the browser when `LLM_SUPPORTS_VISION=true` |
| **Analysts** (one per asset desk, 5) | 09:30 and 17:30 | Read the latest research and signals and save an **analysis note**. Also resolve open coverage requests by assigning symbols to the right cluster |
| **Deals Source Scout** | Every 2 hours, only if some merchants have `pending` or `failed` sources | Find official websites, deal pages and social media accounts for the next batch of merchants |
| **Deals Crawler** | Every 3 hours at :20 | Crawl merchants and bank discount pages and save structured **deals**. Can look up each bank's real cards with `list_bank_cards` so deal card requirements use the same network/tier words as users' cards |
| **Deals Curator** | Daily 03:00 | Expire past deals, remove duplicates, re-check low-confidence deals |

Load: about **150 bot runs on a weekday and 100 on a weekend day**. The 24 hourly crypto runs (2 watchers each) are the biggest share. Thin the crypto and PSX schedules first if the model is slow or costly.

If a wake-up fails, the agent's row in `agent_registry` gets `status = error` and `last_error`. It shows in **Admin → Agents**.

## 2. Per-user teams (message-driven)

Each regular user gets a private room with their own bots. Admin accounts get none. The bots have **no schedule of their own**. They run only when something sends a message into the room.

| Trigger | What happens |
|---|---|
| User sends a chat message or voice note | Goes to the room. The **Finance Assistant** answers by default (when it adds a card it browses the bank's real cards with `list_card_products`). If `DECIDER_BASE_URL` is set, the decision model picks which advisor answers each message |
| **Sunday 19:00** weekly review | The only scheduled job that wakes a per-user bot. Sends the room "weekly check-in: one encouraging message, one concrete tip, one relevant deal if any, at most one question". Only for active, onboarded users whose room is `ready` |
| Deals Advisor recommends a deal | It calls `offer_deal` for each one, which records an offer for that person. From then on, the app watches their bank-alert transactions (see below) |
| A bot replies | The gateway relays OMB's event stream to `POST /api/internal/omb/events`. The backend stores the reply, streams it to the open app and pushes it to the user's devices if they are offline |

### Deal use is detected automatically

When a new debit transaction arrives (Gmail bank alerts or the chat), `detect_redemption` in [deal_detect.py](backend/app/services/deal_detect.py) checks it against the deals that person was offered. It counts as used when all of these hold:

- the transaction is at the deal's merchant and happened **after** the offer, within 14 days of it and inside the deal's own dates and weekdays (Pakistan time);
- if the deal needs a card, the transaction's bank account is at the deal's bank and the person owns a card of that bank that matches it (credit-card deals can't be confirmed from an alert, so those stay manual);
- the amount clears the minimum spend.

The saving is worked out from the amount actually debited (instant discounts are already off it, cashback is not) and capped at the deal's maximum. It goes to savings through the normal deal-saving path, the offer is closed (one redemption per offer, one per transaction), and the person gets "Great, you just saved Rs. X". If the person later tells the assistant about the same purchase, `avail_deal` reports `already_counted` instead of saving it twice. No LLM is involved in detection.

Limits: only deals the advisor offered are tracked (so the advisor must call `offer_deal`); the merchant on the bank alert has to resolve to the same merchant as the deal ("KFC" vs "KFC Pakistan" would be missed); and the debited amount is assumed to be after the discount, so the Rs. figure is announced as "about".

## 3. Scheduled jobs in the worker

Plain code, no bots involved. Two of them call the self-hosted model for small structured tasks (merchant screening, and Gmail parsing when the regex fails). Each job below that notifies creates a notification, which also appears in the chat as an unread "Paisave" message and goes out as a push (VAPID web push). All of them skip admins, inactive users and users who haven't finished onboarding.

| Job | Schedule | Behaviour |
|---|---|---|
| Weekly motivation | Fri 18:00 | "You saved Rs. X this week", or a gentle nudge if nothing was saved |
| Sadqah reminders | Fri 12:00 (friday users), Mon 10:00 (weekly users), 1st of month 10:00 (monthly users) | Only for users who opted in. Amount from their sadqah rule |
| Overspend nudge | Daily 20:30 | Fires if today's spending is above 1.8× the daily budget (70% of monthly income ÷ 30). Transfers, housing, utilities and education are excluded |
| Month-end leftover | Daily 23:30 | Acts only on the last day of the month, for users on "save whatever is left". Moves the unspent income into their goals |
| Merchant screening (uses the self-hosted model) | Every 15 minutes, and just before each Deal Source Scout run | The self-hosted model judges each new merchant from users' spending: a business ("Debited at Kababjees") becomes `pending` and may reach the deal bots; a private payee ("Transfer to Ali Khan") becomes `personal` and never does. If the model is offline the merchant waits as `screening` and is judged later |
| Gmail sync | Every `GMAIL_POLL_MINUTES` (default 5) | Reads new bank alert emails (regex first, LLM parse as fallback) and creates transactions. Posts a quiet "Transactions updated" notice without a push |

## 4. Lifecycle triggers (gateway)

| Trigger | Effect |
|---|---|
| Gateway start | Syncs all shared agents, re-applies per-user teams whose SOUL files changed, removes orphan teams. Retries with backoff until the backend is ready |
| Change to SOUL files, the model (or `DESK_LLM_*`), or the watch clusters | Shared bots are re-applied (hash-based, so unchanged teams are skipped). Per-user teams are re-applied when their stored soul version differs |
| Sign-up verified, or sign-in | The user's room is created in the background if it doesn't exist |
| Admin → Agents → Sync | Forces a full re-sync |
| Admin adds a watch cluster | The cluster gets its own watcher on the next sync |
| Admin deletes a user | Their bots, room and team are removed in OMB. Retried automatically on later syncs if the gateway is down |
| User turns on investments | The Investment Advisor is added to their team on the next re-apply |

## Card catalog

All 23 supported banks and wallets have their card products in the `card_products` table (163 rows when last loaded from [cards.py](backend/app/seed/cards.py); network, tier, debit or credit, Islamic or not, source URL and a confidence of `official`, `bank_site` or `weak`). It is reference data, loaded at every startup including production.

- Users' **Finance Assistant and Deals Advisor** read it with `list_card_products`; `add_card` reports whether the card matches a known product.
- The **Deals Crawler** reads it with `list_bank_cards` so a deal's card requirement uses the same network and tier words as users' cards.
- Some cards have no network because the bank's page didn't say; they match deals that only name a bank and tier.

## Operational notes

- **Needs the models:** sections 1 and 2 and the Gmail LLM fallback depend on a working LLM. Per-user teams (section 2) and the Gmail parse always use the self-hosted model (`LLM_*`). The shared desks (section 1) use it too unless `DESK_LLM_*` is set, in which case they run on that third-party OpenAI-compatible model (and `DESK_LLM_SUPPORTS_VISION` decides whether they get the browser). The worker jobs in section 3 need the model only for merchant screening and the Gmail fallback.
- **Data boundary:** only the shared desks may use the third-party model. Their tools read public market data and shared tables, with no user IDs. The one thing derived from user activity is the merchant names the deals bots receive, and those are screened first (merchant screening, section 3).
- **Push and email are separate:** push notifications need the VAPID keys in the root `.env`. Sign-up codes and password-reset emails need SMTP.
- **Check the schedule is alive:** `docker logs fintechathon-worker-1` prints "scheduler started with N jobs" (19 at the time of writing).
- **Status of verification:** the README notes that scheduled runs have only been verified as far as the trigger call. A full cycle (watchers emit signals, researchers save notes, deal crawlers save deals) has not been confirmed. That is open in the README's Dev deployment TODO.
