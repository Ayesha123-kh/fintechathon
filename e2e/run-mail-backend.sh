#!/bin/bash
# A second backend on :8010 from this checkout, sharing the stack's Postgres and Dragonfly, with SMTP off. The suites
# send only the two emailing calls (sign-up code, password reset) here and read the code / link from its log.
source "$(dirname "$0")/env.sh"
cd "$ROOT/backend"
exec "$E2E/venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8010
