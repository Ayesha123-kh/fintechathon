# Deploying to Railway

Every folder already has a `Dockerfile` and a `railway.json`, so Railway builds each service from its folder.
You need one Railway **project** with 7 services: two databases from Railway's catalogue and five built from this repo.

| Service | Source | Config file | Notes |
|---|---|---|---|
| Postgres | Railway template "PostgreSQL" | n/a | Provides `DATABASE_URL` (superuser) |
| Dragonfly | Docker image `docker.dragonflydb.io/dragonflydb/dragonfly:v1.34.2` | n/a | Add a volume at `/data`, start command `dragonfly --maxmemory=512mb` |
| backend | this repo, root dir `backend` | `backend/railway.json` | API + MCP servers + migrations |
| worker | this repo, root dir `backend` | `backend/railway.worker.json` | Scheduler. Exactly **1** replica |
| omb | this repo, root dir `ai-ml` | `ai-ml/railway.json` | OpenMausBot + gateway. Volume at `/data`, 1 replica |
| frontend | this repo, root dir `frontend` | `frontend/railway.json` | The PWA. The only service with a public domain (plus backend, if you want the API docs) |

## 1. Create the project

1. Push the repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**, then pick the repo. Delete the auto-created service if it has no root dir.
3. **+ New → Database → PostgreSQL**.
4. **+ New → Docker Image** → `docker.dragonflydb.io/dragonflydb/dragonfly:v1.34.2`, and name it `dragonfly`.
5. For each of backend / worker / omb / frontend: **+ New → GitHub Repo**, then:
   - **Settings → Source → Root Directory**: `backend`, `backend`, `ai-ml` or `frontend`.
   - **Settings → Config-as-code → Railway config file**: the path from the table above
     (for the worker it is `/backend/railway.worker.json`).
6. omb: **Settings → Volumes → Add volume** mounted at `/data` (agent memory, OMB config and state live here).

## 2. Variables

Railway private networking: services reach each other at `http://<service-name>.railway.internal:<port>`.
Set `PORT` explicitly for backend (8000) and frontend (3000) so internal URLs are stable.
Use **Shared Variables** (Project Settings → Shared Variables) for the secrets that several services need:

```
INTERNAL_API_KEY=<random>
MCP_USER_TOKEN=<random>
MCP_MARKET_TOKEN=<random>
JWT_SECRET=<random>
ENCRYPTION_KEY=<Fernet key>
APP_DB_PASSWORD=<random>
ADMIN_EMAIL=<admin email: the app admin and the OpenMausBot sign-in>
LLM_BASE_URL=https://<your-vllm-host>/v1
LLM_API_KEY=<key>
LLM_MODEL=qwen3.5-9b
STT_BASE_URL=https://<your-llama-server-stt-host>/v1   # llama.cpp llama-server running Qwen3-ASR
STT_API_KEY=<key>
STT_MODEL=Qwen3-ASR-0.6B
DECIDER_BASE_URL=https://<decision-model-host>/v1   # optional; OMB only accepts https here
DECIDER_API_KEY=...
DECIDER_MODEL=...
```

Generate them with `python -c "import secrets;print(secrets.token_urlsafe(32))"` and
`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`.

**backend** and **worker** (reference the shared variables with `${{shared.NAME}}`):

```
PORT=8000
MIGRATION_DATABASE_URL=${{Postgres.DATABASE_URL}}      # superuser: runs migrations, creates app_user
DATABASE_URL=postgresql+asyncpg://app_user:${{shared.APP_DB_PASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
APP_DB_PASSWORD=${{shared.APP_DB_PASSWORD}}
REDIS_URL=redis://dragonfly.railway.internal:6379/0
OMB_GATEWAY_URL=http://omb.railway.internal:8790
FRONTEND_URL=https://<your-frontend-domain>
PUBLIC_API_URL=https://<your-frontend-domain>/api
CORS_ORIGINS=["https://<your-frontend-domain>"]
COOKIE_SECURE=true
WEBAUTHN_RP_ID=<your-frontend-domain without https://>
... plus every shared variable above (including ADMIN_EMAIL), SMTP_*, VAPID_*, GOOGLE_*, ADMIN_PASSWORD
```

With `ENVIRONMENT=production` the backend and worker refuse to start while `JWT_SECRET`, `INTERNAL_API_KEY` or the
MCP tokens are example values or shorter than 24 characters, `ENCRYPTION_KEY` is empty, `ADMIN_PASSWORD` is shorter
than 12 characters, or `COOKIE_SECURE` isn't `true`. The log names what to fix. Rate limits read the caller's IP from
the right of `X-Forwarded-For`; Railway's edge appends one entry, which is the default `TRUSTED_PROXY_HOPS=1`. Raise it
only if you put another proxy (e.g. a CDN) in front.

`MIGRATION_DATABASE_URL` must use the `postgresql+asyncpg://` scheme. Copy Railway's URL and change the prefix.
The app itself connects as `app_user`, a non-superuser role that the first migration creates. That way
Postgres row level security actually applies (it is bypassed for superusers).

**omb**:

```
BACKEND_URL=http://backend.railway.internal:8000
INTERNAL_API_KEY / MCP_USER_TOKEN / MCP_MARKET_TOKEN / LLM_* / DECIDER_* = the shared variables
LLM_SUPPORTS_VISION=true
DESK_LLM_BASE_URL=https://<third-party-openai-compatible-host>/v1   # optional: shared desks only (public data)
DESK_LLM_API_KEY=<key>
DESK_LLM_MODEL=<model>
DESK_LLM_SUPPORTS_VISION=false
OMB_SIGNIN_EMAILS=${{shared.ADMIN_EMAIL}}           # same admin as the app
```

**frontend**:

```
PORT=3000
BACKEND_INTERNAL_URL=http://backend.railway.internal:8000   # needed at BUILD time (Dockerfile ARG)
```

## 3. Domains and third-party setup

1. frontend → **Settings → Networking → Generate Domain** (or attach your own domain).
2. Google Cloud Console → OAuth client (Web): authorised redirect URI
   `https://<frontend-domain>/api/email/google/callback`. Add your testers under **OAuth consent screen → Test users**
   (Gmail read-only is a restricted scope, so it stays in testing mode until Google verifies the app).
3. Gmail SMTP: turn on 2-Step Verification for the sending account, create an **App Password**,
   and put it in `SMTP_PASSWORD`.
4. VAPID keys for push notifications: `npx web-push generate-vapid-keys`, then set `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`.

## 4. Deploy order and checks

1. Postgres and Dragonfly come first, then backend (its start command runs `alembic upgrade head`), then worker, omb and frontend.
2. `https://<frontend-domain>/api/health` returns `{"ok": true}`.
3. Sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` and open **Admin → Agents**. "OpenMausBot online" should be green and
   the desks should be listed. The first agent sync can take a few minutes.
4. Sign up as a normal user and open the chat. The assistant says "Setting up…" until the user's private team exists.

## Updating agents

Edit any `ai-ml/prompts/<agent>/SOUL.md` and redeploy **omb**. On start, the gateway re-applies only the teams
whose prompts changed. Shared desks are updated right away; every user's private team is re-applied in the background.
You can also press **Admin → Agents → Re-sync agents**.
