# Overview
I want to build a robust and helpful agentic application that serves as a personal financial assistant and advisor to the user to help them with their savings.
# Techstack
1. Python (FastApi, sqlAlchemy, Alembic) for backend/
2. Integration logic for self-hosted headless Openmausbot deployed through docker separately in ai-ml/. Look at its [docs](https://github.com/milind-soni/OpenMausBot/blob/main/docs/self-hosting.md).
3. Tailwind NextJS for frontend/
4. Postgres for database, (dragonfly for caching if needed), (redpanda for message broking if needed)
5. Save all agent prompts as md files like: prompts/<agent_name>/SOUL.md
6. Global docker compose for dev deployment and individual dockerfiles and .env files for each subfolder.
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

The whole project is built and committed (`87e0281` on `main`), and the dev stack is running. I couldn't test it against your real models because there's no vLLM server yet. I did run the full chat loop end to end with a mock OpenAI-compatible model on port 8001, and it works.

**What I tested and saw working:**
- **Accounts and data isolation:** signup and sign-in work. I confirmed the database-level row security directly in Postgres: one user can't read or write another user's rows.
- **Agents:** on startup, all 29 shared agents were created in OpenMausBot: the 5 investment desks (researcher, analyst and watchers) and the Deals Desk.
- **Per-user chat:** each new user gets a private team (Finance Assistant, Savings Coach, Deals Advisor) and their own group chat.
- **Full chat loop:** a message from the web app reached the user's room, and the bot called the user tools with that user's key and got back only that user's data. Its reply then came back into the chat history.
- **Money logic:** I drove the user tools directly as an onboarding chat would (banks, cards, goals, income). A salary credit was automatically split 25% into the goals, and KFC/PSO spends were categorised.
- **Market data:** live prices work for PSX (scraped, because the PSX data API URL returned 404), gold/silver, crypto, foreign stocks, exchange rates and web search.
- **Checks:** 7 backend unit tests pass, the frontend production build passes, and all pages serve.

**Where I departed from the README or your answers, and why:**
- **Per-user bots instead of shared ones.** As you approved: OMB copies a bot's recent activity from its other chats into every prompt, so a shared bot would leak one user's finances into another's chat. Shared desks write to the database instead, and each user's own advisors read it.
- **Member key in the room's standing brief (bulletin), not one tool server per user.** OMB allows at most 20 tool servers per workspace, so I use two. Each user's bots find a random word-style key in their room's bulletin and must pass it on every tool call. Since those bots only ever see their own room, they can't access anyone else's data.
- **Each bot gets only the tools it needs.** By default OMB gave each bot 72 tools (about 22k tokens of descriptions, including creating bots and running commands). A user's bot now gets 32.
- **Gmail uses direct Google OAuth**, as you chose, not OMB's connector (that one is shared across the whole workspace and capped at 5 accounts).

**What you need to provide:**
1. **Models:** your vLLM URLs for the LLM and speech-to-text, in the root `.env` (copy `.env.example`). OMB only accepts the decision model over `https`, or `http` on the same machine.
2. **Third-party credentials:**
   - a Google OAuth client for the email connection, with redirect `http://localhost:3000/api/email/google/callback`
   - a Gmail App Password for password-reset emails
   - VAPID keys for push (`npx web-push generate-vapid-keys`)
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` for the admin account

   All of these go in `backend/.env`.
3. **Fingerprint/face sign-in** works on `localhost`; on a phone it needs HTTPS.

**Not yet verified:**
- How well Qwen 9B handles the tool calls and onboarding conversation.
- The selector I used to allow the researchers' web browser (`mcp:browser:*`) is a guess at OMB's tool name.
- The scheduled proactive messages only ran as far as the trigger call; I didn't run a full scheduled cycle.

The Railway setup is written up in `docs/railway.md`, and the `railway.json` configs are in each folder; we can walk through it when you're ready.

**`/graphify .` results:** the graph has 1,082 nodes, 3,077 edges and 50 communities, in `graphify-out/` (`graph.html`, `GRAPH_REPORT.md`, `graph.json`). I added `graphify-out/` to `.gitignore`. I left the 6 generated app icons out of the extraction because they carry no meaning worth graphing.

The health check flagged 293 edges pointing at nodes that don't exist, 2 self-loops and about 150 duplicate edges collapsed into one. Most look like the usual mismatch between the code-scan and text-scan passes; the graph is still usable.

The most-connected nodes:
1. `system_session()`: 50 edges
2. `Principal`: 48
3. `Base`: 39
4. `scoped_session()`: 37
5. `member()`: 34
6. `UUIDPk`: 31
7. `api()`: 29
8. `notify()`: 25
9. `UserOwned`: 23
10. `Spinner()`: 22

Surprising connections, all inferred:
- `Savings Coach agent` → implements → `Per-user Financial Advisor Teams` (README)
- `Railway Deployment Guide` → references → `omb service` (docker-compose)
- `Offline fallback page` → implements → `Progressive Web App`
- `Investment Advisor agent` → implements → `Investment Advisor Teams`
- `Finance Assistant agent` → implements → `Chat-based Onboarding`

Suggested questions from the graph:
- Why does `Principal` connect the database-session dependencies to auth, dashboard, admin, chat, Gmail and push?
- Are the 26 inferred relationships involving `Principal` actually correct?
- What connects `fintech-agents-gateway`, `fintech-backend` and `react-dom` to the rest of the system? (34 weakly connected nodes)
- Should `Frontend Admin & Config` be split up? (cohesion 0.056)
- Why does `scoped_session()` bridge the gateway's internal API, both MCP servers, auth, dashboard and chat?

The most interesting question the graph can answer: **why does `scoped_session()` bridge the gateway's internal API, both tool servers, auth, dashboard and chat?** That traces how per-user data isolation runs through every entry point. Want me to trace it?
---

# Dev deployment TODO

## 1. Environment files
- [ ] `cp .env.example .env` (root: shared secrets + model URLs used by docker compose)
- [ ] `cp backend/.env.example backend/.env`
- [ ] `cp ai-ml/.env.example ai-ml/.env`
- [ ] `cp frontend/.env.example frontend/.env`
- [ ] Replace every `change-me` value with a random secret: `python -c "import secrets;print(secrets.token_urlsafe(32))"`
  - [ ] Root `.env`: `INTERNAL_API_KEY`, `MCP_USER_TOKEN`, `MCP_MARKET_TOKEN`, `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`
  - [ ] `backend/.env`: `JWT_SECRET`
- [ ] Set `ENCRYPTION_KEY` in `backend/.env` (it encrypts Gmail tokens): `python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`
- [ ] Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env` for the bootstrap admin (or use the demo admin below)

## 2. Models (vLLM, OpenAI compatible)
- [ ] Deploy Qwen3.5-9B with thinking enabled and set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (root `.env`)
- [ ] Set `LLM_SUPPORTS_VISION` in `ai-ml/.env` to match the model. It lets researchers and deal crawlers use OMB's browser.
- [ ] Deploy the speech-to-text model (e.g. Qwen3-ASR-0.6B) and set `STT_BASE_URL`, `STT_API_KEY`, `STT_MODEL` (root `.env`)
- [ ] Deploy the decision model and set `DECIDER_BASE_URL` (must be `https://`), `DECIDER_API_KEY`, `DECIDER_MODEL` in `ai-ml/.env`. Leave empty to have the Finance Assistant answer every message.
- [ ] Verify real tool calling with Qwen: onboarding chat, `get_overview`, `create_goal`, `avail_deal`
- [ ] Verify the browser tool selector `mcp:browser:*` in `ai-ml/gateway/teams.py` matches OMB's real tool names
- [ ] Verify scheduled agent runs: watchers emit signals, researchers save notes, deal crawlers save deals (Admin → Agents)

## 3. Email
- [ ] Gmail SMTP for password resets and test alerts:
  - [ ] Turn on 2-Step Verification on the sending account and create an App Password
  - [ ] Set `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` in `backend/.env`
- [ ] Google OAuth for "Connect Gmail" (read-only):
  - [ ] In Google Cloud Console, create an OAuth client of type Web application
  - [ ] Add the redirect URI `http://localhost:3000/api/email/google/callback`
  - [ ] Enable the Gmail API
  - [ ] Add every tester's Gmail under **OAuth consent screen → Test users**
  - [ ] Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` in `backend/.env`

## 4. Push notifications
- [ ] `npx web-push generate-vapid-keys`, then set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` in `backend/.env`
- [ ] Test on Android/desktop: Settings → Turn on notifications
- [ ] Test on iOS: push only works after "Add to Home Screen" (iOS 16.4+)

## 5. Run
- [ ] `docker compose up -d --build`
- [ ] Check the services:
  - [ ] Web app: http://localhost:3000
  - [ ] API docs: http://localhost:8000/api/docs
  - [ ] Gateway: http://localhost:8790/health
- [ ] Sign in as admin, open **Admin → Agents** and check "OpenMausBot online" and the 29 shared agents
- [ ] Phone testing over the LAN, and fingerprint/face unlock (passkeys), need HTTPS:
  - [ ] Use a tunnel (e.g. `cloudflared tunnel --url http://localhost:3000`)
  - [ ] Set `FRONTEND_URL`, `PUBLIC_API_URL`, `CORS_ORIGINS`, `WEBAUTHN_RP_ID` and `COOKIE_SECURE=true` to the tunnel's domain
  - [ ] Add the tunnel's callback URL to the Google OAuth client

## 6. Demo data (temporary migration `0002_demo_data`)
- [ ] Demo user "Osama": `DEMO_USER_EMAIL` (default `demo@bachat.pk`) / `demo12345`
- [ ] Demo admin: `admin@bachat.pk` / `admin12345`
- [ ] To use a real Gmail for Osama:
  - [ ] Set `DEMO_USER_EMAIL` in `backend/.env`
  - [ ] `docker compose up -d --force-recreate backend worker`
  - [ ] `docker compose exec backend alembic downgrade 0001`
  - [ ] `docker compose exec backend alembic upgrade head`
- [ ] Sign in as Osama, open **Email → Connect Gmail**, then use the navbar **Test bank email** button to send a simulated credit/debit alert
- [ ] Before production, remove the demo data with `alembic downgrade 0001` and delete `backend/alembic/versions/0002_demo_data.py`

## 7. Before Railway
- [ ] Pin the OpenMausBot image to a release tag (`OMB_IMAGE` build arg in `ai-ml/Dockerfile`) instead of `latest`
- [ ] Set `ENVIRONMENT=production`. This hides the test tools and skips the demo migration.
- [ ] Follow `docs/railway.md`
