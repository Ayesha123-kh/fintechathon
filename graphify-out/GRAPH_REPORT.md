# Graph Report - fintechathon  (2026-10-15)

## Corpus Check
- Corpus is ~49,026 words - fits in a single context window. You may not need a graph.

## Summary
- 1082 nodes · 3077 edges · 50 communities (27 shown, 23 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.9)
- Token cost: 123,211 input · 0 output

## Community Hubs (Navigation)
- Frontend Admin & Config
- Market MCP Server
- Gateway Internal API
- User MCP Tools
- Auth & Passkeys
- Investment Desk Prompts
- Dashboard & Finance API
- Frontend Packages & Lint
- Agent Teams & Deployment
- Admin API
- Team File Sync
- Chat API & Streaming
- Gmail Connection API
- Gateway HTTP Endpoints
- Gateway Startup & Scheduler
- RLS Session Dependencies
- TypeScript Config
- Market Tool Wrappers
- Market Data Sources
- OMB HTTP Client
- Web Push API
- LLM & Categorisation
- Backend Railway Config
- AI-ML Railway Config
- Settings & Migrations Env
- Event Relay
- Watchlists & Signals
- Worker Railway Config
- Frontend Railway Config
- MCP Bearer Guard
- Initial Schema & RLS
- OMB Config Init
- Gateway Settings
- Sync State
- PSX Quote
- PSX History
- Web Search
- URL Fetch
- AI-ML Entrypoint
- Crypto Prices
- Metal Prices
- Backend Entrypoint
- PostCSS Config
- Service Worker
- Gateway Project
- Backend Project

## God Nodes (most connected - your core abstractions)
1. `system_session()` - 50 edges
2. `Principal` - 48 edges
3. `Base` - 39 edges
4. `scoped_session()` - 37 edges
5. `member()` - 34 edges
6. `UUIDPk` - 31 edges
7. `api()` - 29 edges
8. `notify()` - 25 edges
9. `UserOwned` - 23 edges
10. `Spinner()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Savings Coach agent` --implements--> `Per-user Financial Advisor Teams`  [INFERRED]
  ai-ml/prompts/savings_advisor/SOUL.md → README.md
- `Railway Deployment Guide` --references--> `omb service (OpenMausBot + agents gateway)`  [INFERRED]
  docs/railway.md → docker-compose.yml
- `Offline fallback page (Bachat)` --implements--> `Progressive Web App (mobile-first)`  [INFERRED]
  frontend/public/offline.html → README.md
- `Investment Advisor agent` --implements--> `Investment Advisor Teams (Gold/Silver, PSX, Foreign, Crypto, Real Estate)`  [INFERRED]
  ai-ml/prompts/investment_advisor/SOUL.md → README.md
- `Finance Assistant agent (private team lead)` --implements--> `Chat-based Onboarding`  [INFERRED]
  ai-ml/prompts/finance_assistant/SOUL.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Desk Lead Analysts (synthesis role)** — ai_ml_prompts_crypto_analyst_soul_crypto_analyst, ai_ml_prompts_foreign_stocks_analyst_soul_global_equities_analyst, ai_ml_prompts_gold_silver_analyst_soul_bullion_analyst, ai_ml_prompts_pk_real_estate_analyst_soul_real_estate_analyst, ai_ml_prompts_psx_analyst_soul_psx_analyst [INFERRED 0.85]
- **Desk Researchers (sourced research notes)** — ai_ml_prompts_crypto_researcher_soul_crypto_researcher, ai_ml_prompts_foreign_stocks_researcher_soul_global_equities_researcher, ai_ml_prompts_gold_silver_researcher_soul_bullion_researcher, ai_ml_prompts_pk_real_estate_researcher_soul_real_estate_researcher, ai_ml_prompts_psx_researcher_soul_psx_researcher [INFERRED 0.85]
- **Cluster Watchers (signal emission)** — ai_ml_prompts_crypto_watcher_soul_crypto_watcher, ai_ml_prompts_foreign_stocks_watcher_soul_global_equities_watcher, ai_ml_prompts_gold_silver_watcher_soul_bullion_watcher, ai_ml_prompts_pk_real_estate_watcher_soul_real_estate_watcher, ai_ml_prompts_psx_watcher_soul_psx_watcher [INFERRED 0.85]
- **Deals Desk pipeline (scout -> crawl -> curate -> advise)** — ai_ml_prompts_deals_source_scout_soul_deals_source_scout, ai_ml_prompts_deals_crawler_soul_deals_crawler, ai_ml_prompts_deals_curator_soul_deals_curator, ai_ml_prompts_deals_advisor_soul_deals_advisor [INFERRED 0.85]
- **Per-user private finance team** — ai_ml_prompts_finance_assistant_soul_finance_assistant, ai_ml_prompts_savings_advisor_soul_savings_coach, ai_ml_prompts_deals_advisor_soul_deals_advisor, ai_ml_prompts_investment_advisor_soul_investment_advisor [EXTRACTED 1.00]
- **Dev docker compose stack** — docker_compose_postgres, docker_compose_dragonfly, docker_compose_backend, docker_compose_worker, docker_compose_omb, docker_compose_frontend [EXTRACTED 1.00]

## Communities (50 total, 23 thin omitted)

### Community 0 - "Frontend Admin & Config"
Cohesion: 0.06
Nodes (106): nextConfig, AdminPage(), AdminUser, Agents, AgentsTab(), Clusters, Deal, DealsTab() (+98 more)

### Community 1 - "Market MCP Server"
Cohesion: 0.05
Nodes (68): google_callback(), add_symbol_to_cluster(), emit_signal(), _mark_run(), save_merchant_sources(), save_research(), set_deal_status(), upsert_deal() (+60 more)

### Community 2 - "Gateway Internal API"
Cohesion: 0.05
Nodes (46): agent_users(), clusters(), omb_events(), OmbEvent, OmbMessage, registry(), RegistryRow, set_soul_version() (+38 more)

### Community 3 - "User MCP Tools"
Cohesion: 0.05
Nodes (34): out(), add_bank_account(), add_card(), avail_deal(), _bank_by_name(), complete_onboarding(), create_goal(), email_connection_status() (+26 more)

### Community 4 - "Auth & Passkeys"
Cohesion: 0.08
Nodes (46): _clear_cookies(), _client_ip(), forgot(), ForgotIn, _login(), _origins(), passkey_auth_options(), passkey_auth_verify() (+38 more)

### Community 5 - "Investment Desk Prompts"
Cohesion: 0.10
Nodes (63): add_symbol_to_cluster() tool, Asset Cluster / Watchlist, Crypto Regulatory & Custody Risk Context, Coverage Request Handling, Crypto Analyst, Crypto Desk, crypto_prices() tool, fx_rates() tool (+55 more)

### Community 6 - "Dashboard & Finance API"
Cohesion: 0.09
Nodes (27): bank_details(), deals(), get_dashboard(), goal_detail(), _goal_out(), list_goals(), me(), MePatch (+19 more)

### Community 7 - "Frontend Packages & Lint"
Cohesion: 0.04
Nodes (44): compat, __dirname, eslintConfig, __filename, dependencies, clsx, lucide-react, next (+36 more)

### Community 8 - "Agent Teams & Deployment"
Cohesion: 0.08
Nodes (33): Deals Advisor agent, Deals Crawler agent, Deals Curator agent (Deals Desk lead), Deals Source Scout agent, fin_user tools (get_overview, avail_deal, ...), Finance Assistant agent (private team lead), member_key (room bulletin), [SCHEDULER] automatic check-ins (+25 more)

### Community 9 - "Admin API"
Cohesion: 0.17
Nodes (21): agents(), agents_sync(), audit(), audit_log(), ClusterIn, ClusterPatch, clusters(), create_cluster() (+13 more)

### Community 10 - "Team File Sync"
Cohesion: 0.16
Nodes (18): apply_user(), _desk_key(), sync_shared(), apply(), ApplyError, _bot_yaml(), BotSpec, _doc() (+10 more)

### Community 11 - "Chat API & Streaming"
Cohesion: 0.13
Nodes (11): history(), message_out(), reset_room(), _send(), SendIn, status(), stream(), events() (+3 more)

### Community 12 - "Gmail Connection API"
Cohesion: 0.11
Nodes (7): connections(), disconnect(), google_start(), sync_now(), csrf_guard(), health(), lifespan()

### Community 13 - "Gateway HTTP Endpoints"
Cohesion: 0.16
Nodes (16): _apply_with_retries(), backend(), force_sync(), health(), internal(), message(), MessageIn, provision() (+8 more)

### Community 14 - "Gateway Startup & Scheduler"
Cohesion: 0.14
Nodes (5): on_startup(), startup_sync(), load_reference_data(), build_scheduler(), main()

### Community 15 - "RLS Session Dependencies"
Cohesion: 0.19
Nodes (10): admin_db(), current_principal(), own_db(), passive_principal(), Principal, require_admin(), require_internal(), _token_from() (+2 more)

### Community 16 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 17 - "Market Tool Wrappers"
Cohesion: 0.12
Nodes (8): expire_past_deals(), fx_rates(), get_watchlist(), global_quote(), list_bank_names(), list_deals(), merchants_needing_sources(), merchants_to_crawl()

### Community 18 - "Market Data Sources"
Cohesion: 0.23
Nodes (10): _cached(), crypto_prices(), fetch(), fx_rates(), fetch(), _get_json(), global_quote(), fetch() (+2 more)

### Community 20 - "Web Push API"
Cohesion: 0.27
Nodes (7): Keys, subscribe(), SubscriptionIn, test(), unsubscribe(), UnsubscribeIn, vapid_key()

### Community 21 - "LLM & Categorisation"
Cohesion: 0.23
Nodes (4): complete_json(), categorize(), llm_category(), rule_category()

### Community 22 - "Backend Railway Config"
Cohesion: 0.18
Nodes (10): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, restartPolicyMaxRetries, restartPolicyType (+2 more)

### Community 23 - "AI-ML Railway Config"
Cohesion: 0.20
Nodes (9): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, numReplicas, restartPolicyType (+1 more)

### Community 24 - "Settings & Migrations Env"
Cohesion: 0.24
Nodes (4): do_run_migrations(), run_migrations_online(), get_settings(), Settings

### Community 26 - "Watchlists & Signals"
Cohesion: 0.22
Nodes (4): list_clusters(), open_coverage_requests(), recent_research(), recent_signals()

### Community 27 - "Worker Railway Config"
Cohesion: 0.22
Nodes (8): build, builder, dockerfilePath, deploy, numReplicas, restartPolicyType, startCommand, $schema

### Community 28 - "Frontend Railway Config"
Cohesion: 0.22
Nodes (8): build, builder, dockerfilePath, deploy, healthcheckPath, restartPolicyMaxRetries, restartPolicyType, $schema

## Knowledge Gaps
- **34 isolated node(s):** `fintech-agents-gateway`, `fintech-backend`, `react-dom`, `@tailwindcss/postcss`, `@types/node` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 371 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Principal` connect `RLS Session Dependencies` to `Auth & Passkeys`, `Dashboard & Finance API`, `Admin API`, `Chat API & Streaming`, `Gmail Connection API`, `Web Push API`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Principal` (e.g. with `agents_sync()` and `audit()`) actually correct?**
  _`Principal` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fintech-agents-gateway`, `fintech-backend`, `react-dom` to the rest of the system?**
  _34 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend Admin & Config` be split into smaller, more focused modules?**
  _Cohesion score 0.05625366999412801 - nodes in this community are weakly interconnected._
- **Why does `scoped_session()` connect `Gateway Internal API` to `Market MCP Server`, `User MCP Tools`, `Auth & Passkeys`, `Dashboard & Finance API`, `Chat API & Streaming`, `RLS Session Dependencies`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Should `Market MCP Server` be split into smaller, more focused modules?**
  _Cohesion score 0.05320634920634921 - nodes in this community are weakly interconnected._
- **Why does `system_session()` connect `Gateway Internal API` to `Market MCP Server`, `Auth & Passkeys`, `Dashboard & Finance API`, `Gateway Startup & Scheduler`, `Market Tool Wrappers`, `Watchlists & Signals`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._