# Overview
I want to build a robust and helpful agentic application that serves as a personal financial assistant and advisor to the user to help them with their savings.
# Techstack
1. Python (FastApi, sqlAlchemy, Alembic) for backend/
2. Integration logic for self-hosted headless Openmausbot deployed through docker separately in ai-ml/. Look at its [docs](https://github.com/milind-soni/OpenMausBot/blob/main/docs/self-hosting.md).
3. Tailwind NextJS for frontend/
4. Postgres for database, (dragonfly for caching if needed), (redpanda for message broking if needed)
5. Save all agent prompts as md files like: prompts/<agent_name>/SOUL.md
6. Global docker compose for dev deployment and individual dockerfiles for each subfolder and one root `.env` that holds every setting.
7. Railways for prod deployment and final testing.
8. Thinking enabled qwen3.5-9b for llm, an stt model and a decision model all deployed on a remote server using vllm and its modules using OpenAI API compatible endpoints.
9. Openmausbot docker-compose. (Agents would be created as parts of teams, and for each user a group chat would be created with memory for that user only.)
# Features/Requirements
1. Progressive webapp mostly to be used on mobile phones but responsive enough for tablet, laptop and desktop screens.
2. SaaS based application with user login/signup, onboarding, dashboard and chat widget who can also send messages to the user without their invocation even if the app is closed as push notification.
3. Follow row level security and role base access control as user and admin. Also make admin dashboard. Don't need payment gateway integration for now but setup db so that it can be done afterwards.
4. Multiple investment advisor teams for different types of investments Gold & Silver, Domestic (Pakistani) Stocks, Foreign Stocks, Crypto Currencies, Pakistani Real Estate. With each team having independent researcher which pulls from credible and trustworthy sources, expert analyzers, separate watchers for each stock whose job is to generate signals.
5. Onboarding includes asking user all the banks where they have an active account, type of debit/credit card they have like `Visa Silver Card of Meezan Bank` so that we can suggest applicable discounts on cards, their saving goals like saving for `a car within a 6 months period with a salary of RS.100,000/month`, connecting their email inboxes to monitor all incoming and outgoing transactions and update the record of funds accordingly, ask how the savings should be separated from the expendable amount for each month and how to divide between multiple simultaneously active goals.
6. The onboarding must be a chat based feature and not form based and everything can be controlled by informing chatbot.
7. There must only be signup, signin, forget password, email connection, dashboard, goal details, bank details screens and a chatbot widget with popup chatbox. Use modular UI with rounded corners and following colors: `#B0E454`, `#224F10`, `#EAFFD0`, `#0D0D0D`.
8. Have a bank apps like login timeout and option for fingerprint or face recognition login.
9. An agentic team that crawls multiple sources to scrape all the deals and discounts in a country, their time limit, if they require a certain card or generic, their type like `fast food restaurant`, `women's apparel`, `men's footwear` etc and maintain a separate db.
10. An agentic financial advisor teams that study users spending habits, their proffered places for personalized discount advises, if they would opt for sadqah reminder. For every discount user avails suggested by the bot the saved amount goes to their savings.
11. User dashboard should have total expendable and savings money and bank wise breakdown about how much is in which bank. It should also show progress of each goal. The chatbot should also give motivational push notifications like `Great! you just saved x amount this week.` Also identify if user is using money for food, grocery, fuel, medicine, misc etc and have the breakdown on the dashboard.
12. The investment advisor board and feature should be optional and must provide a disclaimer if opted for.
13. If there are any changes like user got an increment and tells the chatbot, it should update in its memory and adjust future advises accordingly.
14. All the agents will be created on first startup like migration and then only updated if their soul or instruction files are updated. They would not have any memory except in a group chat to distinguish users. For agents that are not user specific like asset watchers and discount searchers the previous rules doesn't apply and they can have their own memory.

---

# Status (2026-10-20)

Everything in the spec above is built. This section covers what the app does, what runs in the local dev stack today, where the build departs from the spec, and what is still unverified. What wakes each agent and when is in [OMB_AGENTS.md](OMB_AGENTS.md); production deployment is in [docs/railway.md](docs/railway.md).

## What the app does

- **Accounts and security.** Sign-up is confirmed with a 6-digit email code, and nothing is saved until it is entered. Sign-in, forgot password, and a banking-app style lock after 5 idle minutes that opens with the password or fingerprint/face (passkeys). The app connects to Postgres as a non-superuser role, so row level security keeps every user to their own rows. Admin accounts only get the admin dashboard: no finances, goals or assistant.
- **Gmail first, then onboarding by chat.** A new user first connects the Gmail inbox where their bank alerts arrive (read-only). The Finance Assistant then collects banks, cards, income, goals, the savings rule, sadqah reminders and the optional investment board, one topic per message. The reply language is decided from how they answer: English, or Roman Urdu as soon as they write in Urdu (Urdu script only if they ask for it).
- **Chat.** Each user has a private team: Finance Assistant, Savings Coach, Deals Advisor, and the Investment Advisor if they opt in. Replies stream in with live progress (what the bot is thinking, which tool it is using). Voice notes become editable text in the message box: English in Latin letters, Urdu as Roman Urdu (or Urdu script for people who chose it). Notifications arrive as unread chat messages and as web push.
- **Money tracking.** Bank alert emails become transactions (rules first, the self-hosted model as a fallback), alongside anything the person tells the chat. Spending is categorised (food, grocery, fuel, medicine and so on). A salary credit moves the month's savings into goals: equally, by priority, by custom percentages or by deadline. Old alerts never change a balance the person has stated. The dashboard shows total, savings and spendable money, the split per bank, goal progress and spending by category.
- **Cards.** A catalog of 163 card products from all 23 supported banks and wallets. Only real cards can be saved ("Did you mean the Meezan Mastercard Classic Debit Card?"), and never any card digits.
- **Deals.** The Deals Desk finds where merchants publish offers and saves structured deals (bank, card, days, cities, dates). The Deals Advisor recommends the ones that fit the person's cards and habits. When a later bank alert shows a recommended deal was used, the saving moves into their goals and they get "Great, you just saved Rs. X" without telling anyone. Private payees ("Transfer to Ali Khan") are screened out by the self-hosted model before a merchant name can reach the deal bots.
- **Investments (opt-in, with a disclaimer).** Five desks (gold and silver, PSX, foreign stocks, crypto, Pakistani real estate), each with a researcher, an analyst and watchers (16 in all), save signals and research for the Investment Advisor to explain.
- **Scheduled nudges.** Weekly motivation, sadqah reminders, an overspend nudge, a month-end sweep for people who save whatever is left, and a Sunday check-in from the assistant. Days and months follow Pakistan time (Asia/Karachi) whatever timezone the server runs in.
- **Admin dashboard.** Overview, users, agents, plans, deals, companies, banks, cards, tracked assets and watchlists.

## Running locally (checked 2026-10-20)

- The docker compose stack is up; the web app, API and agents gateway all report healthy.
- The models run on the host with llama.cpp `llama-server`, not vLLM yet: Qwen3.5-9B (bf16 GGUF) on port 8001 and Qwen3-ASR-1.7B (Q8_0) on port 8002. `DESK_LLM_*` points the shared desks at the same local server. No decision model is set, so the Finance Assistant answers every message.
- OpenMausBot has all 29 shared agents synced, the event relay is connected and 2 user rooms are ready.
- Agent output so far: the watchers have saved 9 real signals (the last on 2026-10-19). The researchers, analysts and deals bots haven't saved anything yet. A Deals Advisor has recorded a deal offer through its tools, and merchant screening has run (one private payee kept away from the deal bots).
- SMTP, Google OAuth and the VAPID keys are set. No Gmail inbox is connected right now and no bank alerts have been imported into the current database. The demo data (migration `0002`) is loaded.
- Backend tests: 26 pass (`cd backend && uv run pytest`).

## Where the build departs from the spec, and why

- **Per-user bots instead of shared ones.** OpenMausBot copies a bot's recent activity from its other chats into every prompt, so a shared bot would leak one person's finances into another's chat. The shared desks write to the database instead, and each user's own advisors read it.
- **A member key in each room's brief, not one tool server per user.** OpenMausBot allows at most 20 tool servers per workspace, so there are two. Each user's bots find a random word-style key in their room's brief and pass it on every tool call. The key resolves to that one person, and their database session can only reach their rows.
- **Each bot gets only the tools it needs.** By default OpenMausBot offers every bot about 70 tools, including ones that create bots and run commands. A user's bot gets OpenMausBot's built-in tools, 3 memory tools and the 29 `fin_user` tools. Desk bots get the 25 `fin_market` tools instead, plus the browser for researchers and deal bots when their model accepts images.
- **Gmail uses direct Google OAuth,** not OpenMausBot's connector, which is shared by the whole workspace and capped at 5 accounts.
- **Speech-to-text runs on llama.cpp, not vLLM.** Qwen3-ASR has no Urdu and writes Urdu speech in Devanagari; the backend sends llama.cpp a grammar that forces Roman Urdu (or Urdu script) and keeps English in Latin letters.
- **The shared desks may run on a third-party model (`DESK_LLM_*`).** They only handle public data. Per-user teams, merchant screening and bank-email parsing always stay on the self-hosted model.

## Not verified yet

- A full scheduled cycle on the desks: researchers saving notes, analysts saving analysis, deal bots saving deals.
- The whole onboarding conversation with Qwen 9B, start to finish.
- Gmail end to end on the current database: connect an inbox, import alerts, detect a deal being used.
- Whether the browser tool selector `mcp:browser:*` in `ai-ml/gateway/teams.py` matches OpenMausBot's real tool names.
- Push notifications and passkeys on real phones (both need HTTPS).

## Knowledge graph (graphify)

`graphify-out/` is a knowledge graph of the repo, committed with the code: open `graph.html` in a browser, read `GRAPH_REPORT.md` for the summary, or point tools at `graph.json`.

Last updated 2026-10-20: 1,337 nodes, 2,538 edges and 105 communities (76 are large enough to appear in the report). The health check found no dangling or missing edges and no self-loops. The most connected nodes are `Principal` (37 edges, the signed-in caller every API route depends on), `member()` (34, the lookup that turns a bot's member key into one user's database session), the shared model base classes (`Base`, `UserOwned`, `UUIDPk`, `Timestamps`), and `Bank` and `Goal` (21 each).

To refresh it after changes, run graphify with `--update`: it re-extracts only the files that changed, and code files need no LLM.

---

# Dev deployment TODO

`[x]` done · `[❌]` needs your attention · `[ ]` not started yet

## 1. Environment files
- [x] `cp .env.example .env`. This one root file holds every setting for every service. `backend/.env` is a tracked symlink to it (the backend and worker read it whole), and `ai-ml/.env` is a tracked file that pulls only the 16 variables the agents container needs from it (so the JWT, encryption, SMTP, OAuth and database-owner secrets never reach that container). `docker-compose.yml` has no default values.
- [x] Replace every `change-me` value with a random secret: `python -c "import secrets;print(secrets.token_urlsafe(32))"`
  - [x] `INTERNAL_API_KEY`, `MCP_USER_TOKEN`, `MCP_MARKET_TOKEN`, `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `JWT_SECRET`
- [x] Set `ENCRYPTION_KEY` (it encrypts Gmail tokens): `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`
- [x] Set `ADMIN_EMAIL` (also used as the OpenMausBot admin sign-in) and `ADMIN_PASSWORD` for the bootstrap admin (or use the demo admin below)

## 2. Models (OpenAI compatible)
- [x] Dev: Qwen3.5-9B with thinking runs on the host with llama.cpp `llama-server` on port 8001 (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` in the root `.env`)
- [ ] Production: deploy Qwen3.5-9B on the remote server (vLLM, or llama.cpp as in dev) and point `LLM_*` at it
- [❌] `LLM_SUPPORTS_VISION` and `DESK_LLM_SUPPORTS_VISION` are `true`, but the local Qwen server has no vision projector loaded (its `/props` reports `vision: false`). Either start it with its `--mmproj`, or set both to `false` so the researchers and deal bots aren't given a browser they can't see through
- [x] Optional third-party LLM for the shared desks (watchers, researchers, analysts, deals bots), which only handle public data: `DESK_LLM_BASE_URL`, `DESK_LLM_API_KEY`, `DESK_LLM_MODEL`, `DESK_LLM_SUPPORTS_VISION`. Now set to the same local server. Leave the base URL empty to use the self-hosted model. User chats, advisors and bank-email parsing never use it.
- [x] Dev: speech-to-text (Qwen3-ASR, 1.7B Q8_0) runs on llama.cpp `llama-server` with its `--mmproj` on port 8002 (`STT_BASE_URL`, `STT_API_KEY`, `STT_MODEL`). It has to be llama.cpp: the backend sends a GBNF grammar so Urdu comes out in Roman Urdu (or Urdu script for people who chose it) instead of Devanagari
- [ ] Production: deploy the speech-to-text server and point `STT_*` at it
- [ ] Optional: the decision model (`DECIDER_BASE_URL`, which must be `https://`, `DECIDER_API_KEY`, `DECIDER_MODEL`). Empty now, so the Finance Assistant answers every message
- [ ] Verify real tool calling with Qwen: onboarding chat, `get_overview`, `create_goal`, `avail_deal` (so far a Deals Advisor has recorded a deal with `offer_deal`)
- [ ] Verify the browser tool selector `mcp:browser:*` in `ai-ml/gateway/teams.py` matches OMB's real tool names
- [ ] Verify scheduled agent runs (Admin → Agents): the watchers have saved 9 signals; the researchers, analysts and deal bots have saved nothing yet

## 3. Email
- [x] Gmail SMTP for sign-up codes, password resets and test alerts: `SMTP_USERNAME`, `SMTP_PASSWORD` (an App Password; needs 2-Step Verification on the sending account) and `SMTP_FROM` are set in the root `.env`
- [x] Google OAuth for "Connect Gmail" (read-only): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` are set in the root `.env`
- [ ] In Google Cloud Console, check the OAuth client (Web application) has the redirect URI `http://localhost:3000/api/email/google/callback`, the Gmail API is enabled, and every tester's Gmail is under **OAuth consent screen → Test users**
- [ ] Connect a Gmail inbox and confirm bank alerts import (none in the current database)

## 4. Push notifications
- [x] `npx web-push generate-vapid-keys`, then set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` in the root `.env`
- [❌] Test on Android/desktop: Settings → Turn on notifications (no device has subscribed yet)
- [❌] Test on iOS: push only works after "Add to Home Screen" (iOS 16.4+)

## 5. Run
- [x] `docker compose up -d --build`
- [x] Check the services:
  - [x] Web app: http://localhost:3000
  - [x] API docs: http://localhost:8000/api/docs
  - [x] Gateway: http://localhost:8790/health
- [ ] Optional: open the OpenMausBot dashboard with `python3 ai-ml/gateway/omb_ui.py`, then http://127.0.0.1:8799 (no sign-in needed locally)
- [x] Sign in as admin, open **Admin → Agents** and check "OpenMausBot online" and the 29 shared agents
- [x] Backend tests: `cd backend && uv run pytest` (26 pass; the Docker image has no test dependencies)
- [❌] Phone testing over the LAN, and fingerprint/face unlock (passkeys), need HTTPS:
  - [❌] Use a tunnel (e.g. `cloudflared tunnel --url http://localhost:3000`)
  - [❌] Set `FRONTEND_URL`, `PUBLIC_API_URL`, `CORS_ORIGINS`, `WEBAUTHN_RP_ID` and `COOKIE_SECURE=true` to the tunnel's domain
  - [❌] Add the tunnel's callback URL to the Google OAuth client

## 6. Demo data (temporary migration `0002_demo_data`)
- [x] Demo user "Osama": `DEMO_USER_EMAIL` (default `paisave.demo@gmail.com`) / `demo12345`
- [x] Demo admin: the bootstrap admin — `ADMIN_EMAIL` / `ADMIN_PASSWORD` from the root `.env`
- [ ] To use a real Gmail for Osama:
  - [ ] Set `DEMO_USER_EMAIL` in the root `.env`
  - [ ] `docker compose up -d --force-recreate backend worker`
  - [ ] `docker compose exec backend alembic downgrade 0001`
  - [ ] `docker compose exec backend alembic upgrade head`
- [❌] Sign in as Osama, open **Settings (tap your initials) → Connect Gmail**, then use the navbar **Test bank email** button to send a simulated credit/debit alert
- [ ] Before production, remove the demo data with `alembic downgrade 0001` and delete `backend/alembic/versions/0002_demo_data.py`

## 7. Before Railway
- [ ] Deploy the models on the remote server (section 2)
- [ ] Pin the OpenMausBot image to a release tag (`OMB_IMAGE` build arg in `ai-ml/Dockerfile`) instead of `latest`
- [ ] Set `ENVIRONMENT=production`. This hides the test tools and skips the demo migration.
- [ ] Follow `docs/railway.md`
