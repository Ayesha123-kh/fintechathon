from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Saving"
    environment: str = "development"
    # Public URL of the web app (used in emails, OAuth redirects, WebAuthn origin).
    frontend_url: str = "http://localhost:3000"
    # Public URL of this API as seen by the browser (through the Next.js proxy by default).
    public_api_url: str = "http://localhost:3000/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Postgres. The app role must NOT be a superuser or table owner so that RLS applies.
    database_url: str = "postgresql+asyncpg://app_user:app_password@localhost:5432/fintech"
    # Owner role used by Alembic migrations only.
    migration_database_url: str = "postgresql+asyncpg://fintech_owner:owner_password@localhost:5432/fintech"
    app_db_role: str = "app_user"
    app_db_password: str = "app_password"

    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    idle_lock_minutes: int = 5
    cookie_secure: bool = False
    # How many proxies in front of the app append to X-Forwarded-For. The caller's IP (used for rate limits) is that
    # many entries from the right; entries further left were sent by the caller and can be forged. On Railway the
    # edge appends the client's address, so 1. (Next.js itself only fills the header in when it is missing, so in the
    # local stack a client can still choose it; the per-account and per-person limits don't depend on it.)
    trusted_proxy_hops: int = 1
    # Fernet key (urlsafe base64, 32 bytes) used to encrypt OAuth tokens at rest.
    encryption_key: str = ""

    # WebAuthn
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Saving"

    # SMTP (Gmail)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Web Push
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"

    # Google OAuth (Gmail read-only)
    google_client_id: str = ""
    google_client_secret: str = ""
    gmail_poll_minutes: int = 5

    # LLM endpoints (vLLM, OpenAI compatible)
    llm_base_url: str = "http://localhost:8001/v1"
    llm_api_key: str = "EMPTY"
    llm_model: str = "qwen3.5-9b"
    stt_base_url: str = "http://localhost:8002/v1"
    stt_api_key: str = "EMPTY"
    stt_model: str = "Qwen3-ASR-0.6B"

    # OpenMausBot gateway (ai-ml service)
    omb_gateway_url: str = "http://localhost:8790"
    # Shared secret between backend and gateway (both directions).
    internal_api_key: str = "change-me-internal"
    # Bearer tokens OMB sends to our MCP servers.
    mcp_user_token: str = "change-me-mcp-user"
    mcp_market_token: str = "change-me-mcp-market"

    # Bootstrap admin (created on startup if missing)
    admin_email: str = ""
    admin_password: str = ""
    # Login email of the demo user created by the temporary demo-data migration.
    demo_user_email: str = "demo@bachat.pk"

    @property
    def test_tools_enabled(self) -> bool:
        """Simulated bank alert emails and similar helpers; never in production."""
        return self.environment.lower() != "production"

    run_scheduler: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
