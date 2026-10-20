#!/bin/bash
# User-perspective end-to-end checks against the running docker compose stack (web app on :3000).
#
# One-time setup (from the repo root):
#   (cd backend && UV_PROJECT_ENVIRONMENT=../e2e/venv uv sync --frozen)
#   (cd e2e/browser && npm ci || npm i)
# Needs Google Chrome at /usr/bin/google-chrome and the model servers the stack uses.
#
# Uses the demo and admin accounts from migration 0002, creates throwaway e2e-*@example.com users and deletes them
# again, and sends a few real questions to the demo account's assistant. Results land in e2e/results/*.json,
# screenshots in e2e/shots/. The suites run one after another: they share the demo account's chat.
set -u
source "$(dirname "$0")/env.sh"
cd "$E2E"
if ! curl -sf http://127.0.0.1:8010/api/health >/dev/null; then
  ./run-mail-backend.sh > backend-8010.log 2>&1 &
  MAIL_PID=$!
  trap 'kill $MAIL_PID 2>/dev/null' EXIT
  for _ in $(seq 1 60); do curl -sf http://127.0.0.1:8010/api/health >/dev/null && break; sleep 1; done
fi
"$PY" housekeeping.py
"$PY" ingest_check.py "$E2E" 2>&1 | grep -vE ' INFO |^INFO' | tee ingest.log
(cd browser && node e2e.js) 2>&1 | tee browser.log
"$PY" housekeeping.py
"$PY" -u chat_actions.py 2>&1 | tee chat_actions.log
"$PY" -u api_e2e.py 2>&1 | tee api.log
"$PY" housekeeping.py
"$PY" tables.py results > results/tables.md
echo "Done. Per-check tables: e2e/results/tables.md"
