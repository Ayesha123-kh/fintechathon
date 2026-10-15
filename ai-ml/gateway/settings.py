from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenMausBot runs in the same container/network namespace, so loopback = owner access.
    omb_url: str = "http://127.0.0.1:8799"
    omb_data_dir: Path = Path("/data/omb")
    omb_cli: str = "node /app/dist-server/openmausbot.js"
    gateway_state_dir: Path = Path("/data/gateway")
    prompts_dir: Path = Path(__file__).resolve().parent.parent / "prompts"

    # Backend
    backend_url: str = "http://backend:8000"
    internal_api_key: str = "change-me-internal"
    mcp_user_token: str = "change-me-mcp-user"
    mcp_market_token: str = "change-me-mcp-market"

    # Models
    llm_base_url: str = "http://host.docker.internal:8001/v1"
    llm_api_key: str = "EMPTY"
    llm_model: str = "qwen3.5-9b"
    llm_supports_vision: bool = True
    # Optional "decision model" (Jev-like) behind an OpenAI-compatible endpoint. OMB requires https,
    # or http on this machine only. Empty disables automatic routing (the Finance Assistant leads).
    decider_base_url: str = ""
    decider_api_key: str = ""
    decider_model: str = ""

    instance_id: str = "vllm"
    relay_final_after_seconds: float = 4.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
