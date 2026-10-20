# Sourced by the e2e scripts: the dev stack's settings from the root .env, pointed at the ports docker compose
# publishes on this machine. SMTP is switched off, so sign-up codes and reset links are logged instead of emailed.
E2E="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$E2E")"
v() { grep -E "^$1=" "$ROOT/.env" | head -1 | cut -d= -f2-; }
export DATABASE_URL="postgresql+asyncpg://$(v APP_DB_ROLE):$(v APP_DB_PASSWORD)@127.0.0.1:5433/$(v POSTGRES_DB)"
export MIGRATION_DATABASE_URL="postgresql+asyncpg://$(v POSTGRES_USER):$(v POSTGRES_PASSWORD)@127.0.0.1:5433/$(v POSTGRES_DB)"
export REDIS_URL="redis://127.0.0.1:6380/0" OMB_GATEWAY_URL="http://127.0.0.1:8790"
export LLM_BASE_URL="http://127.0.0.1:8001/v1" STT_BASE_URL="http://127.0.0.1:8002/v1"
export SMTP_USERNAME="" SMTP_PASSWORD=""
export PYTHONPATH="$ROOT/backend"
PY="$E2E/venv/bin/python"
