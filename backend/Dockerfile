FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
# Strip CRLF (Windows checkouts) or the script fails with "not found".
RUN sed -i "s/\r$//" docker-entrypoint.sh && chmod +x docker-entrypoint.sh
ENV PATH="/app/.venv/bin:$PATH" PORT=8000
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
# "api" (default) runs migrations then the API; "worker" runs the scheduler.
CMD ["api"]
