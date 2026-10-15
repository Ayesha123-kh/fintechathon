# OpenMausBot + the gateway in one container: the gateway reaches OMB over loopback
# (trusted as owner) and OMB itself is never exposed. Pin OMB_IMAGE to a v… tag for production.
ARG OMB_IMAGE=ghcr.io/milind-soni/openmausbot:latest
FROM ${OMB_IMAGE}

USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv tini \
  && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

WORKDIR /gateway
COPY pyproject.toml uv.lock ./
RUN UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev --no-install-project --python /usr/bin/python3 \
  && chown -R maus:maus /gateway
COPY --chown=maus:maus gateway ./gateway
COPY --chown=maus:maus prompts ./prompts
COPY --chown=maus:maus docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

USER maus
ENV PATH="/gateway/.venv/bin:$PATH" \
    OMB_DATA_DIR=/data/omb \
    OMB_PORT=8799 \
    OMB_WEBHOOK_PORT=8800 \
    GATEWAY_STATE_DIR=/data/gateway \
    PROMPTS_DIR=/gateway/prompts \
    GATEWAY_PORT=8790
EXPOSE 8790
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
  CMD curl -sf http://127.0.0.1:8790/health || exit 1
ENTRYPOINT ["/usr/bin/tini", "--", "/gateway/docker-entrypoint.sh"]
