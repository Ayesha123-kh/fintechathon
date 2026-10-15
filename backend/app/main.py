import contextlib
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, auth, chat, email, finance, internal, push
from app.core.config import settings
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


for r in (auth.router, finance.router, chat.router, email.router, push.router, admin.router, internal.router):
    app.include_router(r, prefix="/api")

# MCP servers for OpenMausBot (not exposed through the web proxy).
app.mount("/mcp/user", BearerGuard(user_mcp_app, settings.mcp_user_token))
app.mount("/mcp/market", BearerGuard(market_mcp_app, settings.mcp_market_token))


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "backend"}
