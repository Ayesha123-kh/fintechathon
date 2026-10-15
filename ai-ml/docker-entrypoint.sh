#!/bin/bash
# Starts OpenMausBot (loopback only) and the gateway; if either exits, the container exits.
set -euo pipefail
mkdir -p "$OMB_DATA_DIR" "$GATEWAY_STATE_DIR"

cd /gateway && python -m gateway.config_init

# This container is the only OpenMausBot using the volume. A lease left by a killed previous
# container names a PID that may now belong to an unrelated process here, so clear it.
rm -f "$OMB_DATA_DIR/openmausbot-server.lease"

cd /app && node dist-server/server-launcher.js &
OMB_PID=$!

cd /gateway && uvicorn gateway.main:app --host 0.0.0.0 --port "${GATEWAY_PORT:-8790}" &
GW_PID=$!

trap 'kill -TERM $OMB_PID $GW_PID 2>/dev/null; wait $OMB_PID 2>/dev/null' TERM INT
wait -n $OMB_PID $GW_PID
EXIT=$?
kill -TERM $OMB_PID $GW_PID 2>/dev/null || true
exit $EXIT
