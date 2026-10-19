import contextlib
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, auth, chat, dev, email, finance, internal, push
from app.core.cache import rate_limit, redis
from app.core.config import settings
from app.core.deps import _token_from, client_ip
from app.core.security import decode_access_token
from app.mcp import market_server, user_server
from app.mcp.common import BearerGuard
from app.seed.loader import ensure_admin, load_reference_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

user_mcp_app = user_server.build_app()
market_mcp_app = market_server.build_app()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    await load_reference_data()
    await ensure_admin()
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(user_server.mcp.session_manager.run())
        await stack.enter_async_context(market_server.mcp.session_manager.run())
        yield


app = FastAPI(title=f"{settings.app_name} API", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """Cookie-authenticated writes must carry a custom header, which cross-site forms cannot send."""
    path = request.url.path
    if (request.method in UNSAFE and path.startswith("/api/") and not path.startswith("/api/internal/")
            and request.headers.get("x-requested-with") != "bachat"):
        return JSONResponse({"detail": "csrf_header_missing"}, status_code=403)
    return await call_next(request)


USER_RATE, ANON_RATE = 600, 300  # requests a minute: per signed-in person, else per address


@app.middleware("http")
async def global_rate_limit(request: Request, call_next):
    """One ceiling on any caller's request rate, on top of the per-endpoint limits (the gateway is exempt)."""
    path = request.url.path
    if path.startswith("/api/") and not path.startswith(("/api/internal/", "/api/health")):
        token = _token_from(request)
        payload = decode_access_token(token) if token else None
        key, limit = (f"api:u:{payload['sub']}", USER_RATE) if payload else (f"api:ip:{client_ip(request)}", ANON_RATE)
        if not await rate_limit(key, limit, 60):
            retry = await redis.ttl(f"rl:{key}")
            return JSONResponse({"detail": "slow_down"}, status_code=429, headers={"Retry-After": str(max(retry, 1))})
    return await call_next(request)


for r in (auth.router, finance.router, chat.router, email.router, push.router, admin.router, internal.router, dev.router):
    app.include_router(r, prefix="/api")

# MCP servers for OpenMausBot (not exposed through the web proxy).
app.mount("/mcp/user", BearerGuard(user_mcp_app, settings.mcp_user_token))
app.mount("/mcp/market", BearerGuard(market_mcp_app, settings.mcp_market_token))


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "backend"}
