# Graph Report - .  (2026-10-18)

## Corpus Check
- 26 files · ~66,317 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1181 nodes · 2418 edges · 91 communities (67 shown, 24 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 471 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Auth and Sign-up API|Auth and Sign-up API]]
- [[_COMMUNITY_Demo Data Migration|Demo Data Migration]]
- [[_COMMUNITY_Agents Gateway Main|Agents Gateway Main]]
- [[_COMMUNITY_User MCP Server|User MCP Server]]
- [[_COMMUNITY_Desk Prompts (Bullion)|Desk Prompts (Bullion)]]
- [[_COMMUNITY_Finance Tests and Types|Finance Tests and Types]]
- [[_COMMUNITY_Dashboard and Goal Pages|Dashboard and Goal Pages]]
- [[_COMMUNITY_Deal Detection Service|Deal Detection Service]]
- [[_COMMUNITY_Test Alerts and Email Matching|Test Alerts and Email Matching]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Cache and Scheduled Jobs|Cache and Scheduled Jobs]]
- [[_COMMUNITY_Agent Team Catalog|Agent Team Catalog]]
- [[_COMMUNITY_OMB Event Relay|OMB Event Relay]]
- [[_COMMUNITY_Sign-in and Reset Pages|Sign-in and Reset Pages]]
- [[_COMMUNITY_App Layout and Service Worker|App Layout and Service Worker]]
- [[_COMMUNITY_Admin API|Admin API]]
- [[_COMMUNITY_Principal and DB Deps|Principal and DB Deps]]
- [[_COMMUNITY_Admin Dashboard Page|Admin Dashboard Page]]
- [[_COMMUNITY_Agents Doc and Desk LLM|Agents Doc and Desk LLM]]
- [[_COMMUNITY_App Shell and Settings|App Shell and Settings]]
- [[_COMMUNITY_TypeScript Config|TypeScript Config]]
- [[_COMMUNITY_README and Railway Guide|README and Railway Guide]]
- [[_COMMUNITY_Chat Widget and Stream|Chat Widget and Stream]]
- [[_COMMUNITY_Dev Tools and App Entry|Dev Tools and App Entry]]
- [[_COMMUNITY_OMB Gateway Client|OMB Gateway Client]]
- [[_COMMUNITY_Finance API|Finance API]]
- [[_COMMUNITY_Gmail Sync Service|Gmail Sync Service]]
- [[_COMMUNITY_Crypto Desk Prompts|Crypto Desk Prompts]]
- [[_COMMUNITY_Finance Assistant Prompt|Finance Assistant Prompt]]
- [[_COMMUNITY_Goal and Profile Tools|Goal and Profile Tools]]
- [[_COMMUNITY_Compose Dev Stack|Compose Dev Stack]]
- [[_COMMUNITY_Deals Advisor Prompt|Deals Advisor Prompt]]
- [[_COMMUNITY_Market MCP Server|Market MCP Server]]
- [[_COMMUNITY_MCP Bearer Guard|MCP Bearer Guard]]
- [[_COMMUNITY_Chat API|Chat API]]
- [[_COMMUNITY_LLM Client|LLM Client]]
- [[_COMMUNITY_Card Catalog Tools|Card Catalog Tools]]
- [[_COMMUNITY_Onboarding and Card Privacy Rules|Onboarding and Card Privacy Rules]]
- [[_COMMUNITY_Market Reference Tools|Market Reference Tools]]
- [[_COMMUNITY_Chat Unread and Room Sync|Chat Unread and Room Sync]]
- [[_COMMUNITY_Signals and Coverage Tools|Signals and Coverage Tools]]
- [[_COMMUNITY_Railway Config A|Railway Config A]]
- [[_COMMUNITY_Railway Config B|Railway Config B]]
- [[_COMMUNITY_Email API|Email API]]
- [[_COMMUNITY_Push API|Push API]]
- [[_COMMUNITY_Crypto and Member Keys|Crypto and Member Keys]]
- [[_COMMUNITY_Railway Worker Config|Railway Worker Config]]
- [[_COMMUNITY_Railway Config C|Railway Config C]]
- [[_COMMUNITY_Deals Crawler Prompt|Deals Crawler Prompt]]
- [[_COMMUNITY_Merchant Screening Tests|Merchant Screening Tests]]
- [[_COMMUNITY_Initial Schema and RLS|Initial Schema and RLS]]
- [[_COMMUNITY_Spending Tools|Spending Tools]]
- [[_COMMUNITY_ESLint Config|ESLint Config]]
- [[_COMMUNITY_Alembic Env|Alembic Env]]
- [[_COMMUNITY_Entrypoint Script A|Entrypoint Script A]]
- [[_COMMUNITY_Deals Curator Agent|Deals Curator Agent]]
- [[_COMMUNITY_Deals Source Scout Agent|Deals Source Scout Agent]]
- [[_COMMUNITY_Tool: expire_past_deals|Tool: expire_past_deals]]
- [[_COMMUNITY_Tool: fetch_url|Tool: fetch_url]]
- [[_COMMUNITY_Tool: fx_rates|Tool: fx_rates]]
- [[_COMMUNITY_Tool: get_watchlist|Tool: get_watchlist]]
- [[_COMMUNITY_Tool: global_quote|Tool: global_quote]]
- [[_COMMUNITY_Tool: list_deals|Tool: list_deals]]
- [[_COMMUNITY_Tool: merchants_to_crawl|Tool: merchants_to_crawl]]
- [[_COMMUNITY_Tool: psx_quote|Tool: psx_quote]]
- [[_COMMUNITY_Tool: web_search|Tool: web_search]]
- [[_COMMUNITY_Card Catalog Data|Card Catalog Data]]
- [[_COMMUNITY_Seed Data|Seed Data]]
- [[_COMMUNITY_Entrypoint Script B|Entrypoint Script B]]
- [[_COMMUNITY_Next Config|Next Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Compose Services|Compose Services]]
- [[_COMMUNITY_Service Worker|Service Worker]]
- [[_COMMUNITY_Goal Model|Goal Model]]
- [[_COMMUNITY_Gateway Package|Gateway Package]]
- [[_COMMUNITY_Backend Package|Backend Package]]

## God Nodes (most connected - your core abstractions)
1. `Principal` - 66 edges
2. `member()` - 33 edges
3. `api()` - 27 edges
4. `upgrade()` - 25 edges
5. `Base` - 25 edges
6. `UserOwned` - 25 edges
7. `scoped_session()` - 24 edges
8. `UUIDPk` - 24 edges
9. `Timestamps` - 24 edges
10. `User` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Per-user bots instead of shared ones` --semantically_similar_to--> `Per-user teams`  [INFERRED] [semantically similar]
  README.md → OMB_AGENTS.md
- `Qwen3.5-9B vLLM models (LLM, STT, decision)` --semantically_similar_to--> `Self-hosted model (LLM_*)`  [INFERRED] [semantically similar]
  README.md → OMB_AGENTS.md
- `Optional DESK_LLM_* third-party desk model` --semantically_similar_to--> `Third-party desk LLM (DESK_LLM_*)`  [INFERRED] [semantically similar]
  README.md → OMB_AGENTS.md
- `Scheduled runs not fully verified` --semantically_similar_to--> `Scheduled run verification status`  [INFERRED] [semantically similar]
  README.md → OMB_AGENTS.md
- `Railway services (7)` --semantically_similar_to--> `postgres service`  [INFERRED] [semantically similar]
  docs/railway.md → docker-compose.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Deal offer to automatic redemption flow** — omb_agents_offer_deal, omb_agents_detect_redemption, omb_agents_avail_deal_already_counted, ai_ml_prompts_deals_advisor_soul_offer_deal_rule [EXTRACTED 1.00]
- **Third-party desk LLM data boundary** — omb_agents_desk_llm, omb_agents_self_hosted_model, omb_agents_merchant_screening, omb_agents_data_boundary, omb_agents_shared_desks [EXTRACTED 1.00]
- **Card catalog readers** — omb_agents_card_products_table, omb_agents_list_card_products, omb_agents_list_bank_cards, omb_agents_finance_assistant, omb_agents_deals_advisor, omb_agents_deals_crawler [EXTRACTED 1.00]
- **Crypto desk flow (watcher signals, researcher notes, analyst synthesis)** — ai_ml_prompts_crypto_watcher_soul_crypto_watcher, ai_ml_prompts_crypto_researcher_soul_crypto_researcher, ai_ml_prompts_crypto_analyst_soul_crypto_analyst [EXTRACTED 0.95]
- **Desk researcher-watcher-analyst pipeline** — ai_ml_prompts_psx_researcher_soul_agent, ai_ml_prompts_psx_watcher_soul_agent, ai_ml_prompts_psx_analyst_soul_agent, ai_ml_prompts_investment_advisor_soul_agent [INFERRED 0.85]

## Communities (91 total, 24 thin omitted)

### Community 0 - "Auth and Sign-up API"
Cohesion: 0.06
Nodes (89): _clear_cookies(), _client_ip(), forgot(), ForgotIn, _login(), _origins(), _otp_hash(), passkey_auth_options() (+81 more)

### Community 1 - "Demo Data Migration"
Cohesion: 0.08
Nodes (64): _at(), downgrade(), date, datetime, TEMPORARY demo data: a long-time user with ~4 months of history, plus a demo adm, Categories, banks, asset classes and plans normally load at app startup, i.e. af, _seed_reference(), _skip() (+56 more)

### Community 2 - "Agents Gateway Main"
Cohesion: 0.06
Nodes (40): build(), main(), Write OpenMausBot's config.json before the server starts (instances are read at, apply_user(), _apply_with_retries(), backend(), deprovision(), deprovision_user() (+32 more)

### Community 3 - "User MCP Server"
Cohesion: 0.09
Nodes (39): complete_onboarding(), email_connection_status(), find_deals(), follow_asset(), forget_fact(), list_banks(), market_research(), market_signals() (+31 more)

### Community 4 - "Desk Prompts (Bullion)"
Cohesion: 0.06
Nodes (40): Bullion Researcher agent prompt, Per-tola price formula and bullion drivers, Credible sources only policy, Research cycle (save_research note), Bullion Watcher agent prompt, Per-tola price formula and bullion drivers, Watch cycle (emit_signal), Investment Advisor agent prompt (+32 more)

### Community 5 - "Finance Tests and Types"
Cohesion: 0.14
Nodes (33): Category, add_savings(), allocate_income(), Allocation, dashboard(), _detect_deal_use(), money(), monthly_savings_target() (+25 more)

### Community 6 - "Dashboard and Goal Pages"
Cohesion: 0.11
Nodes (29): Dashboard, DashboardView(), fmtDate(), Goal, GoalPage(), SOURCE, openSettings(), Account (+21 more)

### Community 7 - "Deal Detection Service"
Cohesion: 0.12
Nodes (30): detect_redemption(), _eligible_card_label(), _in_window(), _money(), AsyncSession, datetime, Decimal, UUID (+22 more)

### Community 8 - "Test Alerts and Email Matching"
Cohesion: 0.14
Nodes (28): avail_deal(), get_overview(), Everything about the person at a glance: profile, onboarding progress, banks, ca, The person used a suggested discount. The amount saved is moved into their savin, Bank, BankAccount, Card, DealOffer (+20 more)

### Community 9 - "Frontend Dependencies"
Cohesion: 0.07
Nodes (29): dependencies, clsx, lucide-react, next, react, react-dom, @simplewebauthn/browser, swr (+21 more)

### Community 10 - "Cache and Scheduled Jobs"
Cohesion: 0.11
Nodes (26): _active_users(), _bots(), month_end_leftover(), overspend_nudge(), Scheduled work: waking shared agent teams, Gmail sync and proactive nudges to us, The assistant reaches out on its own; replies arrive as push notifications if th, For people who save 'whatever is left', move the month's unspent income into goa, Evening nudge when today's spending is well above the person's daily budget. (+18 more)

### Community 11 - "Agent Team Catalog"
Cohesion: 0.14
Nodes (23): apply(), ApplyError, _bot_yaml(), BotSpec, desk_model_ref(), desk_supports_vision(), _doc(), _hash() (+15 more)

### Community 12 - "OMB Event Relay"
Cohesion: 0.11
Nodes (17): Every second: send changed messages (streaming) and finalise quiet ones., Relay, _cached(), crypto_prices(), fx_rates(), _get_json(), global_quote(), metal_price() (+9 more)

### Community 13 - "Sign-in and Reset Pages"
Cohesion: 0.19
Nodes (17): Request(), Reset(), SignIn(), Pending, SignUp(), VerifyCode(), AuthShell(), LockScreen() (+9 more)

### Community 14 - "App Layout and Service Worker"
Cohesion: 0.11
Nodes (17): jakarta, metadata, viewport, ServiceWorker(), ApiError, ERRORS, Listener, lockListeners (+9 more)

### Community 15 - "Admin API"
Cohesion: 0.22
Nodes (21): agents(), agents_sync(), audit(), ClusterIn, ClusterPatch, clusters(), create_cluster(), DealPatch (+13 more)

### Community 16 - "Principal and DB Deps"
Cohesion: 0.16
Nodes (20): usage(), admin_db(), current_principal(), own_db(), passive_principal(), passive_user_principal(), Principal, AsyncSession (+12 more)

### Community 17 - "Admin Dashboard Page"
Cohesion: 0.15
Nodes (19): AdminUser, Agents, AgentsTab(), Clusters, Deal, DealsTab(), Overview(), Plan (+11 more)

### Community 18 - "Agents Doc and Desk LLM"
Cohesion: 0.14
Nodes (20): DESK_LLM_* env vars, Worker exactly 1 replica, OpenMausBot agents: triggers and routines, agent_registry table, Analysts (5), Card catalog, Data boundary rule, Deals Crawler (+12 more)

### Community 19 - "App Shell and Settings"
Cohesion: 0.20
Nodes (15): AppShell(), EmailResult, initials(), SettingsPanel(), ThemePicker(), guessDevice(), registerPasskey(), currentSubscription() (+7 more)

### Community 20 - "TypeScript Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 21 - "README and Railway Guide"
Cohesion: 0.12
Nodes (19): member_key rule, member_key rule (fin_user tools), app_user non-superuser role, Scheduled run verification status, fintechathon README, Deals crawling team requirement, Optional DESK_LLM_* third-party desk model, Dev deployment TODO (+11 more)

### Community 22 - "Chat Widget and Stream"
Cohesion: 0.14
Nodes (15): Server-sent events with new / updated chat messages. Also marks the user as onli, stream(), AdminPage(), Home(), ChatWidget(), inline(), isAfter(), Msg (+7 more)

### Community 23 - "Dev Tools and App Entry"
Cohesion: 0.13
Nodes (13): AsyncIOScheduler, Testing helpers, available only outside production., test_alert(), csrf_guard(), lifespan(), Request, Cookie-authenticated writes must carry a custom header, which cross-site forms c, ensure_admin() (+5 more)

### Community 24 - "OMB Gateway Client"
Cohesion: 0.22
Nodes (17): _call(), deprovision_user(), ensure_room(), gateway_status(), gateway_usage(), GatewayError, UUID, Client for the ai-ml gateway that fronts OpenMausBot, and per-user room provisio (+9 more)

### Community 25 - "Finance API"
Cohesion: 0.23
Nodes (16): bank_details(), deals(), get_dashboard(), goal_detail(), _goal_out(), list_goals(), me(), MePatch (+8 more)

### Community 26 - "Gmail Sync Service"
Cohesion: 0.22
Nodes (15): auth_url(), exchange_code(), llm_parse(), parse_email(), UUID, Gmail (read-only) connection and bank-alert ingestion.  Only messages from the a, Fetch new alert emails from the user's banks and turn them into transactions., redirect_uri() (+7 more)

### Community 27 - "Crypto Desk Prompts"
Cohesion: 0.24
Nodes (15): Coverage request handling (add_symbol_to_cluster), Crypto Analyst agent, Crypto regulatory and custody risk context, Balanced and humble analyst rules (no leverage), save_research tool, Credible sources policy (crypto), Crypto Researcher agent, Crypto Watcher agent (+7 more)

### Community 28 - "Finance Assistant Prompt"
Cohesion: 0.15
Nodes (15): Finance Assistant SOUL prompt, avail_deal for used discounts, remember_fact / chat-controlled updates, [SCHEDULER] messages handling, Style rules (language mirroring, Islamic finance aware), omb service (Railway), omb variables (DESK_LLM_*, DECIDER_*), Updating agents via SOUL.md redeploy (+7 more)

### Community 29 - "Goal and Profile Tools"
Cohesion: 0.17
Nodes (15): create_goal(), move_to_savings(), _parse_date(), preview_savings_split(), date, Update the financial profile. savings_mode: 'percent' of income (savings_value =, Create a saving goal, e.g. 'Car' Rs. 1,500,000 by 2027-04-30. deadline is YYYY-M, Change a goal (target, deadline, priority, weight) or pause / cancel it. (+7 more)

### Community 30 - "Compose Dev Stack"
Cohesion: 0.26
Nodes (15): docker-compose.yml dev stack, backend service, dragonfly service, frontend service, LLM_* and STT_* env vars, omb service, postgres service, Shared secrets (INTERNAL_API_KEY, MCP tokens) (+7 more)

### Community 31 - "Deals Advisor Prompt"
Cohesion: 0.23
Nodes (13): Deals Advisor SOUL prompt, Automatic deal detection (do not ask if used), avail_deal fallback (already_counted), Deals Advisor workflow (get_overview, find_deals), Never invent deals rule, offer_deal rule, Team roster (Savings Coach, Deals Advisor, Investment Advisor), avail_deal already_counted (+5 more)

### Community 32 - "Market MCP Server"
Cohesion: 0.15
Nodes (11): crypto_prices(), list_bank_names(), merchants_needing_sources(), metal_price(), psx_history(), `fin_market` MCP server: tools for the shared teams (researchers, analysts, watc, Merchants (new ones come from users' spending) whose website and social accounts, Bank names to use in upsert_deal.bank. (+3 more)

### Community 33 - "MCP Bearer Guard"
Cohesion: 0.17
Nodes (9): ASGIApp, BearerGuard, out(), Any, ASGI wrapper: only callers presenting the configured bearer token reach the MCP, Make tool results JSON friendly (Decimal, UUID, datetime)., Receive, Scope (+1 more)

### Community 34 - "Chat API"
Cohesion: 0.26
Nodes (11): history(), message_out(), datetime, UUID, Retry provisioning after an error., reset_room(), _send(), SendIn (+3 more)

### Community 35 - "LLM Client"
Cohesion: 0.20
Nodes (10): complete_json(), Any, Direct calls to the self-hosted models (vLLM, OpenAI-compatible).  Agents run in, Ask for a JSON object. Thinking is disabled for these short extraction calls., transcribe(), categorize(), llm_category(), Spending categories: merchant directory first, keyword rules second, LLM last. (+2 more)

### Community 36 - "Card Catalog Tools"
Cohesion: 0.21
Nodes (12): list_bank_cards(), The card products one bank issues (name, network, tier, debit/credit) from our c, add_bank_account(), add_card(), _bank_by_name(), list_card_products(), _product_row(), The cards a bank issues (name, network, tier, debit/credit), from our catalog. O (+4 more)

### Community 37 - "Onboarding and Card Privacy Rules"
Cohesion: 0.20
Nodes (11): No card digits/CVV/PIN/OTP rule, Onboarding cards step (list_card_products, add_card), Investment opt-in with disclaimer, No card digits/CVV/PIN/OTP rule, Chat-based onboarding flow (10 steps), Sadqah reminders step, Savings rule and goal split, card_products table (+3 more)

### Community 38 - "Market Reference Tools"
Cohesion: 0.18
Nodes (11): ASSET_CLASSES, list_clusters(), open_coverage_requests(), Watch clusters (groups of related assets, one watcher bot each)., Signals emitted recently (to avoid duplicates and for analysts)., Store a research or analysis note. sources must be URLs of credible sources you, Research and analysis notes from the last few days., Assets users asked about that no watcher covers yet. (+3 more)

### Community 39 - "Chat Unread and Room Sync"
Cohesion: 0.22
Nodes (11): mark_read(), AsyncSession, Bot replies and notifications that arrived since the person last opened the chat, unread(), agent_users(), Every provisioned room, so the gateway can re-apply bots when SOUL files change., Financial profile the chatbot fills in during onboarding and keeps up to date., UserProfile (+3 more)

### Community 40 - "Signals and Coverage Tools"
Cohesion: 0.18
Nodes (11): add_symbol_to_cluster(), emit_signal(), _mark_run(), Publish a signal for one asset. confidence 0..1. rationale: 1-3 sentences citing, Assign a requested asset to the most fitting existing cluster (resolves coverage, Save the official website / deals page / social media accounts of a Pakistani me, Insert or update a deal. deal_type is the specific kind, e.g. 'fast food restaur, Curator: expire, reject or re-activate a deal. (+3 more)

### Community 41 - "Railway Config A"
Cohesion: 0.18
Nodes (10): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, restartPolicyMaxRetries, restartPolicyType (+2 more)

### Community 42 - "Railway Config B"
Cohesion: 0.20
Nodes (9): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, numReplicas, restartPolicyType (+1 more)

### Community 43 - "Email API"
Cohesion: 0.27
Nodes (9): connections(), disconnect(), google_callback(), google_start(), AsyncSession, Request, UUID, sync_now() (+1 more)

### Community 44 - "Push API"
Cohesion: 0.31
Nodes (7): Keys, AsyncSession, subscribe(), SubscriptionIn, test(), unsubscribe(), UnsubscribeIn

### Community 45 - "Crypto and Member Keys"
Cohesion: 0.31
Nodes (7): decrypt(), encrypt(), _fernet(), member_key(), Opaque per-user handle given to that user's bots (room bulletin).      Word-styl, _access_token(), revoke()

### Community 46 - "Railway Worker Config"
Cohesion: 0.22
Nodes (8): build, builder, dockerfilePath, deploy, numReplicas, restartPolicyType, startCommand, $schema

### Community 47 - "Railway Config C"
Cohesion: 0.22
Nodes (8): build, builder, dockerfilePath, deploy, healthcheckPath, restartPolicyMaxRetries, restartPolicyType, $schema

### Community 48 - "Deals Crawler Prompt"
Cohesion: 0.43
Nodes (8): Deals Crawler SOUL prompt, Bank card discounts cycle, Deal confidence scoring (0.9/0.6/<0.5), Dedupe via list_deals, list_bank_cards usage, merchants_to_crawl cycle, Only save what was seen rule, upsert_deal tool

### Community 50 - "Initial Schema and RLS"
Cohesion: 0.50
Nodes (3): apply_security(), Create the RLS-restricted application role and row level security policies., upgrade()

### Community 51 - "Spending Tools"
Cohesion: 0.40
Nodes (5): list_transactions(), Recent transactions, newest first., Spending habits: totals by category, top merchants, daily average, income in the, spending_summary(), Transaction

### Community 52 - "ESLint Config"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

## Knowledge Gaps
- **143 isolated node(s):** `docker-entrypoint.sh script`, `fintech-agents-gateway`, `$schema`, `builder`, `dockerfilePath` (+138 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Principal` connect `Principal and DB Deps` to `Auth and Sign-up API`, `Chat API`, `Chat Unread and Room Sync`, `Email API`, `Push API`, `Admin API`, `Chat Widget and Stream`, `Dev Tools and App Entry`, `Finance API`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Bank` connect `Test Alerts and Email Matching` to `Demo Data Migration`, `User MCP Server`, `Card Catalog Tools`, `Finance Tests and Types`, `Deal Detection Service`, `Signals and Coverage Tools`, `Dev Tools and App Entry`, `Finance API`, `Gmail Sync Service`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `upgrade()` connect `Demo Data Migration` to `Auth and Sign-up API`, `Test Alerts and Email Matching`, `Goal and Profile Tools`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Principal` (e.g. with `ClusterIn` and `ClusterPatch`) actually correct?**
  _`Principal` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `upgrade()` (e.g. with `hash_password()` and `Bank`) actually correct?**
  _`upgrade()` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `docker-entrypoint.sh script`, `Gateway between the backend and OpenMausBot.  Runs next to OMB (same container /`, `Re-apply per-user teams whose SOUL files changed since they were created.` to the rest of the system?**
  _332 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Auth and Sign-up API` be split into smaller, more focused modules?**
  _Cohesion score 0.05696636925188744 - nodes in this community are weakly interconnected._