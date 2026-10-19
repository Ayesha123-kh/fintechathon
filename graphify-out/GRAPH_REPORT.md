# Graph Report - .  (2026-10-20)

## Corpus Check
- 52 files · ~74,688 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1337 nodes · 2538 edges · 105 communities (76 shown, 29 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 455 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Finance Models and Money Logic|Finance Models and Money Logic]]
- [[_COMMUNITY_Models, Demo Data and Notify|Models, Demo Data and Notify]]
- [[_COMMUNITY_Agents Gateway Sync|Agents Gateway Sync]]
- [[_COMMUNITY_Room Provisioning and Chat API|Room Provisioning and Chat API]]
- [[_COMMUNITY_Admin Dashboard Pages|Admin Dashboard Pages]]
- [[_COMMUNITY_Investment Desk Prompts|Investment Desk Prompts]]
- [[_COMMUNITY_Admin API|Admin API]]
- [[_COMMUNITY_App Shell and Chat Widget|App Shell and Chat Widget]]
- [[_COMMUNITY_OMB Relay and Market Data|OMB Relay and Market Data]]
- [[_COMMUNITY_Internal API and App Entry|Internal API and App Entry]]
- [[_COMMUNITY_Gmail Alert Parsing|Gmail Alert Parsing]]
- [[_COMMUNITY_Dashboard Charts and Modals|Dashboard Charts and Modals]]
- [[_COMMUNITY_Sign-up and Password Reset|Sign-up and Password Reset]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Agent Team Catalog|Agent Team Catalog]]
- [[_COMMUNITY_User Tools Lists and Onboarding|User Tools: Lists and Onboarding]]
- [[_COMMUNITY_Deal Detection Service|Deal Detection Service]]
- [[_COMMUNITY_Principal and DB Deps|Principal and DB Deps]]
- [[_COMMUNITY_Auth Pages and Lock Screen|Auth Pages and Lock Screen]]
- [[_COMMUNITY_Sign-in, Unlock and Passkeys|Sign-in, Unlock and Passkeys]]
- [[_COMMUNITY_Scheduled User Jobs|Scheduled User Jobs]]
- [[_COMMUNITY_Shared Desks and Model Routing|Shared Desks and Model Routing]]
- [[_COMMUNITY_TypeScript Config|TypeScript Config]]
- [[_COMMUNITY_Session and API Client|Session and API Client]]
- [[_COMMUNITY_README Design Decisions|README Design Decisions]]
- [[_COMMUNITY_Server Sessions and Idle Lock|Server Sessions and Idle Lock]]
- [[_COMMUNITY_User Tools Deals and Accounts|User Tools: Deals and Accounts]]
- [[_COMMUNITY_Crypto and Equities Desk Prompts|Crypto and Equities Desk Prompts]]
- [[_COMMUNITY_Market Server Data Tools|Market Server Data Tools]]
- [[_COMMUNITY_Card Catalog Matching|Card Catalog Matching]]
- [[_COMMUNITY_Compose and Railway Setup|Compose and Railway Setup]]
- [[_COMMUNITY_Chat Onboarding Flow|Chat Onboarding Flow]]
- [[_COMMUNITY_User Tools Goals and Profile|User Tools: Goals and Profile]]
- [[_COMMUNITY_Deals Advisor and Detection|Deals Advisor and Detection]]
- [[_COMMUNITY_Deals Crawler and Card Lookups|Deals Crawler and Card Lookups]]
- [[_COMMUNITY_Finance Assistant and Gateway|Finance Assistant and Gateway]]
- [[_COMMUNITY_MCP Bearer Guard|MCP Bearer Guard]]
- [[_COMMUNITY_Signals and Research Tools|Signals and Research Tools]]
- [[_COMMUNITY_Request Schemas and Push API|Request Schemas and Push API]]
- [[_COMMUNITY_Backend Railway Config|Backend Railway Config]]
- [[_COMMUNITY_Root Layout and Theme|Root Layout and Theme]]
- [[_COMMUNITY_Passkey and Push Clients|Passkey and Push Clients]]
- [[_COMMUNITY_Agents Railway Config|Agents Railway Config]]
- [[_COMMUNITY_RLS Sessions|RLS Sessions]]
- [[_COMMUNITY_Speech-to-Text|Speech-to-Text]]
- [[_COMMUNITY_Spending Categorisation|Spending Categorisation]]
- [[_COMMUNITY_Pakistan Time Helpers|Pakistan Time Helpers]]
- [[_COMMUNITY_Desk Write Tools|Desk Write Tools]]
- [[_COMMUNITY_Worker Railway Config|Worker Railway Config]]
- [[_COMMUNITY_Frontend Railway Config|Frontend Railway Config]]
- [[_COMMUNITY_Investment Tools (Opt-in)|Investment Tools (Opt-in)]]
- [[_COMMUNITY_Merchant Screening|Merchant Screening]]
- [[_COMMUNITY_Merchant Screening Tests|Merchant Screening Tests]]
- [[_COMMUNITY_README Status and Catalog|README Status and Catalog]]
- [[_COMMUNITY_Deal Upsert and Fingerprints|Deal Upsert and Fingerprints]]
- [[_COMMUNITY_Mobile Tab Bar|Mobile Tab Bar]]
- [[_COMMUNITY_Initial Schema and RLS|Initial Schema and RLS]]
- [[_COMMUNITY_ESLint Config|ESLint Config]]
- [[_COMMUNITY_Alembic Environment|Alembic Environment]]
- [[_COMMUNITY_Add Bank Account Tool|Add Bank Account Tool]]
- [[_COMMUNITY_PCM Recorder Worklet|PCM Recorder Worklet]]
- [[_COMMUNITY_OMB Dashboard Forwarder|OMB Dashboard Forwarder]]
- [[_COMMUNITY_Agents Container Entrypoint|Agents Container Entrypoint]]
- [[_COMMUNITY_Deals Curator Prompt|Deals Curator Prompt]]
- [[_COMMUNITY_Deals Source Scout Prompt|Deals Source Scout Prompt]]
- [[_COMMUNITY_Crypto Prices Tool|Crypto Prices Tool]]
- [[_COMMUNITY_Fetch URL Tool|Fetch URL Tool]]
- [[_COMMUNITY_FX Rates Tool|FX Rates Tool]]
- [[_COMMUNITY_Global Quote Tool|Global Quote Tool]]
- [[_COMMUNITY_List Deals Tool|List Deals Tool]]
- [[_COMMUNITY_Merchants Needing Sources|Merchants Needing Sources]]
- [[_COMMUNITY_PSX History Tool|PSX History Tool]]
- [[_COMMUNITY_Web Search Tool|Web Search Tool]]
- [[_COMMUNITY_Card Catalog Seed|Card Catalog Seed]]
- [[_COMMUNITY_Reference Seed Data|Reference Seed Data]]
- [[_COMMUNITY_Backend Entrypoint|Backend Entrypoint]]
- [[_COMMUNITY_Next.js Config|Next.js Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Offline Page|Offline Page]]
- [[_COMMUNITY_Service Worker|Service Worker]]
- [[_COMMUNITY_Goal Reference|Goal Reference]]
- [[_COMMUNITY_Any Typing Reference|Any Typing Reference]]
- [[_COMMUNITY_Goal Type Reference|Goal Type Reference]]
- [[_COMMUNITY_User Reference|User Reference]]
- [[_COMMUNITY_Gateway Project Metadata|Gateway Project Metadata]]
- [[_COMMUNITY_Backend Project Metadata|Backend Project Metadata]]
- [[_COMMUNITY_UserProfile Reference|UserProfile Reference]]

## God Nodes (most connected - your core abstractions)
1. `Principal` - 37 edges
2. `member()` - 34 edges
3. `upgrade()` - 25 edges
4. `Base` - 25 edges
5. `UserOwned` - 25 edges
6. `UUIDPk` - 24 edges
7. `Timestamps` - 24 edges
8. `Bank` - 21 edges
9. `Goal` - 21 edges
10. `api()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Email OTP sign-up` --references--> `signup_verify()`  [INFERRED]
  README.md → backend/app/api/auth.py
- `Idle lock with password or passkey unlock` --references--> `session_state()`  [INFERRED]
  README.md → backend/app/core/security.py
- `Admin accounts are admin-only` --references--> `user_principal()`  [INFERRED]
  README.md → backend/app/core/deps.py
- `Live agent activity in chat` --references--> `Relay`  [INFERRED]
  README.md → ai-ml/gateway/relay.py
- `Vision flags on but local Qwen has no vision projector` --conceptually_related_to--> `desk_supports_vision()`  [INFERRED]
  README.md → ai-ml/gateway/teams.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Deal offer to automatic redemption flow** — omb_agents_offer_deal, omb_agents_detect_redemption, omb_agents_avail_deal_already_counted, ai_ml_prompts_deals_advisor_soul_offer_deal_rule [EXTRACTED 1.00]
- **Third-party desk LLM data boundary** — omb_agents_desk_llm, omb_agents_self_hosted_model, omb_agents_merchant_screening, omb_agents_data_boundary, omb_agents_shared_desks [EXTRACTED 1.00]
- **Card catalog readers** — omb_agents_card_products_table, omb_agents_list_card_products, omb_agents_list_bank_cards, omb_agents_finance_assistant, omb_agents_deals_advisor, omb_agents_deals_crawler [EXTRACTED 1.00]
- **Per-user data isolation design** — readme_per_user_bots_decision, readme_member_key_bulletin, readme_row_level_security, readme_tool_allowlist [INFERRED 0.85]
- **Crypto desk flow (watcher signals, researcher notes, analyst synthesis)** — ai_ml_prompts_crypto_watcher_soul_crypto_watcher, ai_ml_prompts_crypto_researcher_soul_crypto_researcher, ai_ml_prompts_crypto_analyst_soul_crypto_analyst [EXTRACTED 0.95]
- **Desk researcher-watcher-analyst pipeline** — ai_ml_prompts_psx_researcher_soul_agent, ai_ml_prompts_psx_watcher_soul_agent, ai_ml_prompts_psx_analyst_soul_agent, ai_ml_prompts_investment_advisor_soul_agent [INFERRED 0.85]

## Communities (105 total, 29 thin omitted)

### Community 0 - "Finance Models and Money Logic"
Cohesion: 0.06
Nodes (83): bank_details(), deals(), get_dashboard(), goal_detail(), _goal_out(), list_goals(), me(), MePatch (+75 more)

### Community 1 - "Models, Demo Data and Notify"
Cohesion: 0.07
Nodes (66): _at(), downgrade(), date, datetime, TEMPORARY demo data: a long-time user with ~4 months of history, plus a demo adm, Categories, banks, asset classes and plans normally load at app startup, i.e. af, _seed_reference(), _skip() (+58 more)

### Community 2 - "Agents Gateway Sync"
Cohesion: 0.06
Nodes (41): build(), main(), Write OpenMausBot's config.json before the server starts (instances are read at, apply_user(), _apply_with_retries(), backend(), deprovision(), deprovision_user() (+33 more)

### Community 3 - "Room Provisioning and Chat API"
Cohesion: 0.07
Nodes (53): history(), mark_read(), message_out(), AsyncSession, datetime, Principal, UUID, Server-sent events with new / updated chat messages. Also marks the user as onli (+45 more)

### Community 4 - "Admin Dashboard Pages"
Cohesion: 0.06
Nodes (23): Agents, Asset, Assets, CLASS_LABEL, SIGNAL_TONE, Bank, KINDS, CardRow (+15 more)

### Community 5 - "Investment Desk Prompts"
Cohesion: 0.06
Nodes (40): Bullion Researcher agent prompt, Per-tola price formula and bullion drivers, Credible sources only policy, Research cycle (save_research note), Bullion Watcher agent prompt, Per-tola price formula and bullion drivers, Watch cycle (emit_signal), Investment Advisor agent prompt (+32 more)

### Community 6 - "Admin API"
Cohesion: 0.12
Nodes (38): agents(), agents_sync(), audit(), audit_log(), banks(), card_catalog(), ClusterIn, ClusterPatch (+30 more)

### Community 7 - "App Shell and Chat Widget"
Cohesion: 0.08
Nodes (26): Dashboard, DashboardView(), ADMIN_NAV, AdminSidebar(), AdminTabs(), Item, useActive(), AppShell() (+18 more)

### Community 8 - "OMB Relay and Market Data"
Cohesion: 0.07
Nodes (21): Every second: send changed messages (streaming), live turn activity, and finalis, Note a sign of life in a room's turn (and what it is doing now)., Relay, _cached(), crypto_prices(), fx_rates(), _get_json(), global_quote() (+13 more)

### Community 9 - "Internal API and App Entry"
Cohesion: 0.08
Nodes (26): AsyncIOScheduler, Testing helpers, available only outside production., known_users(), omb_events(), OmbEvent, OmbMessage, OmbStatus, Endpoints only the ai-ml gateway calls (shared secret in `x-internal-key`). (+18 more)

### Community 10 - "Gmail Alert Parsing"
Cohesion: 0.10
Nodes (31): _access_token(), auth_url(), exchange_code(), find_merchant(), llm_parse(), _match_account(), must_connect_first(), parse_email() (+23 more)

### Community 11 - "Dashboard Charts and Modals"
Cohesion: 0.10
Nodes (23): fmtDate(), Goal, GoalPage(), SOURCE, Account, BankModal(), Banks, CardRow (+15 more)

### Community 12 - "Sign-up and Password Reset"
Cohesion: 0.13
Nodes (28): _client_ip(), forgot(), ForgotIn, _origins(), _otp_hash(), passkey_delete(), passkey_register_verify(), PasskeyVerifyIn (+20 more)

### Community 13 - "Frontend Dependencies"
Cohesion: 0.07
Nodes (29): dependencies, clsx, lucide-react, next, react, react-dom, @simplewebauthn/browser, swr (+21 more)

### Community 14 - "Agent Team Catalog"
Cohesion: 0.14
Nodes (23): apply(), ApplyError, _bot_yaml(), BotSpec, desk_model_ref(), desk_supports_vision(), _doc(), _hash() (+15 more)

### Community 15 - "User Tools: Lists and Onboarding"
Cohesion: 0.12
Nodes (22): complete_onboarding(), email_connection_status(), find_deals(), list_banks(), list_transactions(), member(), preview_savings_split(), `fin_user` MCP server: the tools a user's private bots use to read and change th (+14 more)

### Community 16 - "Deal Detection Service"
Cohesion: 0.17
Nodes (21): detect_redemption(), _in_window(), _money(), AsyncSession, datetime, Decimal, UUID, Notice that a person used a deal they were told about, from their spending alone (+13 more)

### Community 17 - "Principal and DB Deps"
Cohesion: 0.16
Nodes (20): admin_db(), current_principal(), own_db(), passive_principal(), passive_user_principal(), Principal, AsyncSession, Request (+12 more)

### Community 18 - "Auth Pages and Lock Screen"
Cohesion: 0.20
Nodes (15): Request(), Reset(), SignIn(), Pending, SignUp(), VerifyCode(), AuthShell(), LockScreen() (+7 more)

### Community 19 - "Sign-in, Unlock and Passkeys"
Cohesion: 0.21
Nodes (21): _clear_cookies(), _login(), passkey_auth_verify(), passkey_register_options(), PasskeyAuthIn, Request, User, Lets the app decide between sign-in, lock screen and the dashboard on launch. (+13 more)

### Community 20 - "Scheduled User Jobs"
Cohesion: 0.15
Nodes (19): _active_users(), _bots(), month_end_leftover(), overspend_nudge(), Scheduled work: waking shared agent teams, Gmail sync and proactive nudges to us, The assistant reaches out on its own; replies arrive as push notifications if th, For people who save 'whatever is left', move the month's unspent income into goa, Evening nudge when today's spending is well above the person's daily budget. (+11 more)

### Community 21 - "Shared Desks and Model Routing"
Cohesion: 0.13
Nodes (20): omb service (Railway), omb variables (DESK_LLM_*, DECIDER_*), Worker exactly 1 replica, agent_registry table, Analysts (5), Data boundary rule, Deals Curator, Deals Source Scout (+12 more)

### Community 22 - "TypeScript Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 23 - "Session and API Client"
Cohesion: 0.15
Nodes (15): Home(), ApiError, ERRORS, Listener, lockListeners, logoutListeners, onLocked(), onLoggedOut() (+7 more)

### Community 24 - "README Design Decisions"
Cohesion: 0.16
Nodes (18): member_key rule, member_key rule (fin_user tools), Models on the host (host.docker.internal *_BASE_URL), Scheduled run verification status, fintechathon README, Backend tests (uv run pytest), Dev deployment TODO, Gmail via direct Google OAuth (+10 more)

### Community 25 - "Server Sessions and Idle Lock"
Cohesion: 0.24
Nodes (17): _active_key(), create_session(), decode_access_token(), get_session(), UUID, Passwords, JWT access tokens and server-side sessions with an idle lock.  Sessio, Validate a refresh token and issue a new one for the same session., Returns (sid, refresh_token). (+9 more)

### Community 26 - "User Tools: Deals and Accounts"
Cohesion: 0.12
Nodes (17): avail_deal(), forget_fact(), offer_deal(), UUID, Save a lasting fact about the person (life events, increments, preferences, fami, Retire a remembered fact that is no longer true., Correct an account's balance or details (e.g. when the person tells you their cu, Remove an account the person closed or no longer uses. (+9 more)

### Community 27 - "Crypto and Equities Desk Prompts"
Cohesion: 0.24
Nodes (15): Coverage request handling (add_symbol_to_cluster), Crypto Analyst agent, Crypto regulatory and custody risk context, Balanced and humble analyst rules (no leverage), save_research tool, Credible sources policy (crypto), Crypto Researcher agent, Crypto Watcher agent (+7 more)

### Community 28 - "Market Server Data Tools"
Cohesion: 0.13
Nodes (13): expire_past_deals(), get_watchlist(), list_bank_names(), merchants_to_crawl(), metal_price(), psx_quote(), `fin_market` MCP server: tools for the shared teams (researchers, analysts, watc, The symbols a watcher must check this cycle. (+5 more)

### Community 29 - "Card Catalog Matching"
Cohesion: 0.19
Nodes (14): list_bank_cards(), The card products one bank issues (name, network, tier, debit/credit) from our c, add_card(), list_card_products(), _product_row(), The cards a bank issues (name, network, tier, debit/credit), from our catalog. O, Save a debit/credit card, e.g. 'Visa Gold debit card of Meezan Bank' -> bank='Me, CardProduct (+6 more)

### Community 30 - "Compose and Railway Setup"
Cohesion: 0.26
Nodes (15): docker-compose.yml dev stack, ai-ml/.env (only the variables omb needs), backend service, dragonfly service, frontend service, omb service, postgres service, Root .env (every setting, nothing defaulted in compose) (+7 more)

### Community 31 - "Chat Onboarding Flow"
Cohesion: 0.14
Nodes (14): No card digits/CVV/PIN/OTP rule, Onboarding cards step (real catalog cards only, did_you_mean), Investment opt-in with disclaimer, No card digits/CVV/PIN/OTP rule, Chat-based onboarding flow (10 steps), Sadqah reminders step, Savings rule and goal split, app_user non-superuser role (+6 more)

### Community 32 - "User Tools: Goals and Profile"
Cohesion: 0.16
Nodes (14): create_goal(), get_overview(), move_to_savings(), _parse_date(), date, Everything about the person at a glance: profile, onboarding progress, banks, ca, Update the financial profile. savings_mode: 'percent' of income (savings_value =, Create a saving goal, e.g. 'Car' Rs. 1,500,000 by 2027-04-30. deadline is YYYY-M (+6 more)

### Community 33 - "Deals Advisor and Detection"
Cohesion: 0.23
Nodes (13): Deals Advisor SOUL prompt, Automatic deal detection (do not ask if used), avail_deal fallback (already_counted), Never invent deals rule, offer_deal rule, avail_deal for used discounts, Team roster (Savings Coach, Deals Advisor, Investment Advisor), avail_deal already_counted (+5 more)

### Community 34 - "Deals Crawler and Card Lookups"
Cohesion: 0.24
Nodes (13): Deals Advisor workflow (get_overview, find_deals), Deals Crawler SOUL prompt, Bank card discounts cycle, Deal confidence scoring (0.9/0.6/<0.5), Dedupe via list_deals, list_bank_cards usage, merchants_to_crawl cycle, Only save what was seen rule (+5 more)

### Community 35 - "Finance Assistant and Gateway"
Cohesion: 0.19
Nodes (13): Finance Assistant SOUL prompt, Reply language decided from answers (Roman Urdu preferred), remember_fact / chat-controlled updates, [SCHEDULER] messages handling, Style rules (bulletin reply language, Islamic finance aware), Updating agents via SOUL.md redeploy, Finance Assistant, Gateway (backend to OMB bridge) (+5 more)

### Community 36 - "MCP Bearer Guard"
Cohesion: 0.17
Nodes (9): ASGIApp, BearerGuard, out(), Any, ASGI wrapper: only callers presenting the configured bearer token reach the MCP, Make tool results JSON friendly (Decimal, UUID, datetime)., Receive, Scope (+1 more)

### Community 37 - "Signals and Research Tools"
Cohesion: 0.18
Nodes (11): ASSET_CLASSES, list_clusters(), open_coverage_requests(), Watch clusters (groups of related assets, one watcher bot each)., Signals emitted recently (to avoid duplicates and for analysts)., Store a research or analysis note. sources must be URLs of credible sources you, Research and analysis notes from the last few days., Assets users asked about that no watcher covers yet. (+3 more)

### Community 38 - "Request Schemas and Push API"
Cohesion: 0.27
Nodes (9): PasskeyLoginOptionsIn, UnlockIn, Keys, AsyncSession, subscribe(), SubscriptionIn, unsubscribe(), UnsubscribeIn (+1 more)

### Community 39 - "Backend Railway Config"
Cohesion: 0.18
Nodes (10): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, restartPolicyMaxRetries, restartPolicyType (+2 more)

### Community 40 - "Root Layout and Theme"
Cohesion: 0.20
Nodes (5): jakarta, metadata, viewport, ServiceWorker(), ThemeChoice

### Community 41 - "Passkey and Push Clients"
Cohesion: 0.35
Nodes (9): api(), authenticateWithPasskey(), guessDevice(), registerPasskey(), currentSubscription(), disablePush(), enablePush(), pushSupported() (+1 more)

### Community 42 - "Agents Railway Config"
Cohesion: 0.20
Nodes (9): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, numReplicas, restartPolicyType (+1 more)

### Community 43 - "RLS Sessions"
Cohesion: 0.36
Nodes (9): passkey_auth_options(), passkey_list(), _apply_context(), AsyncSession, UUID, Database engine and RLS-aware sessions.  Every session runs inside one transacti, A transaction scoped to one user (role 'user'), an admin ('admin') or background, scoped_session() (+1 more)

### Community 44 - "Speech-to-Text"
Cohesion: 0.24
Nodes (9): Speech to text only: the app puts the text in the message box for the person to, transcribe_voice(), Direct calls to the self-hosted models (vLLM, OpenAI-compatible).  Agents run in, transcribe(), Shared Variables, STT on llama.cpp llama-server (Qwen3-ASR), Speech-to-text on llama.cpp (Urdu grammar), Voice notes to editable text (+1 more)

### Community 45 - "Spending Categorisation"
Cohesion: 0.28
Nodes (8): Any, complete_json(), Ask for a JSON object. Thinking is disabled for these short extraction calls., categorize(), llm_category(), Spending categories: merchant directory first, keyword rules second, LLM last., Returns (category, subcategory such as 'fast food restaurant')., rule_category()

### Community 46 - "Pakistan Time Helpers"
Cohesion: 0.42
Nodes (8): day_start(), month_start(), date, datetime, Pakistan time. "Today", "this month" and a deal's dates are Pakistani calendar d, Midnight in Pakistan at the start of `day` (default: today)., Midnight in Pakistan on the first of `day`'s month (default: this month)., today()

### Community 47 - "Desk Write Tools"
Cohesion: 0.22
Nodes (9): add_symbol_to_cluster(), emit_signal(), _mark_run(), Publish a signal for one asset. confidence 0..1. rationale: 1-3 sentences citing, Assign a requested asset to the most fitting existing cluster (resolves coverage, Save the official website / deals page / social media accounts of a Pakistani me, Curator: expire, reject or re-activate a deal., save_merchant_sources() (+1 more)

### Community 48 - "Worker Railway Config"
Cohesion: 0.22
Nodes (8): build, builder, dockerfilePath, deploy, numReplicas, restartPolicyType, startCommand, $schema

### Community 49 - "Frontend Railway Config"
Cohesion: 0.22
Nodes (8): build, builder, dockerfilePath, deploy, healthcheckPath, restartPolicyMaxRetries, restartPolicyType, $schema

### Community 50 - "Investment Tools (Opt-in)"
Cohesion: 0.25
Nodes (8): follow_asset(), market_research(), market_signals(), AsyncSession, Latest signals from the watcher bots. asset_class: gold_silver, psx, foreign_sto, Recent research and expert analysis notes for an asset class (opt-in only)., Follow an asset. If no watcher covers it yet, a coverage request is filed so the, _require_investor()

### Community 51 - "Merchant Screening"
Cohesion: 0.32
Nodes (7): classify_payee(), Keep private payees away from the shared deal bots.  The merchant directory is g, True for a business, False for a person, None when the model could not be asked., Judge merchants that were waiting for the model. Returns how many were decided., screen_pending_merchants(), status_for(), Merchant screening (private payees hidden)

### Community 53 - "README Status and Catalog"
Cohesion: 0.29
Nodes (8): OpenMausBot agents: triggers and routines, Card catalog, Admin dashboard (10 pages), Card catalog (163 products, 23 banks), Idle lock with password or passkey unlock, Email OTP sign-up, Pakistan time for days and months, Status (2026-10-20)

### Community 54 - "Deal Upsert and Fingerprints"
Cohesion: 0.33
Nodes (7): Insert or update a deal. deal_type is the specific kind, e.g. 'fast food restaur, upsert_deal(), deal_fingerprint(), date, normalize_name(), Normalize a merchant name so 'KFC PAKISTAN (PVT) LTD - DHA' and 'kfc' match., test_normalize_merchant()

### Community 55 - "Mobile Tab Bar"
Cohesion: 0.40
Nodes (4): isTab(), Tab, TABS, useMobileTab()

### Community 56 - "Initial Schema and RLS"
Cohesion: 0.50
Nodes (3): apply_security(), Create the RLS-restricted application role and row level security policies., upgrade()

### Community 58 - "ESLint Config"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 60 - "Add Bank Account Tool"
Cohesion: 0.50
Nodes (4): add_bank_account(), _bank_by_name(), Bank, Add a bank account or wallet the person actively uses.

## Knowledge Gaps
- **156 isolated node(s):** `docker-entrypoint.sh script`, `fintech-agents-gateway`, `$schema`, `builder`, `dockerfilePath` (+151 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Status (2026-10-20)` connect `README Status and Catalog` to `Deals Advisor and Detection`, `Finance Assistant and Gateway`, `Internal API and App Entry`, `Speech-to-Text`, `Principal and DB Deps`, `Merchant Screening`, `README Design Decisions`, `Compose and Railway Setup`, `Chat Onboarding Flow`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `Notification` connect `Models, Demo Data and Notify` to `Passkey and Push Clients`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `upgrade()` connect `Models, Demo Data and Notify` to `Finance Models and Money Logic`, `Sign-in, Unlock and Passkeys`, `Sign-up and Password Reset`, `Deal Upsert and Fingerprints`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Principal` (e.g. with `ForgotIn` and `PasskeyAuthIn`) actually correct?**
  _`Principal` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `upgrade()` (e.g. with `hash_password()` and `Bank`) actually correct?**
  _`upgrade()` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `Base` (e.g. with `AssetClass` and `CoverageRequest`) actually correct?**
  _`Base` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `docker-entrypoint.sh script`, `Gateway between the backend and OpenMausBot.  Runs next to OMB (same container /`, `Re-apply per-user teams whose SOUL files changed since they were created.` to the rest of the system?**
  _363 weakly-connected nodes found - possible documentation gaps or missing edges._