"""Write OpenMausBot's config.json before the server starts (instances are read at boot).

Merges into an existing file so settings changed later through OMB itself are kept,
and only overwrites the keys this deployment owns: the vLLM engine instance, the
decision model, the two MCP servers that point at our backend, and feature flags.
"""

import json
import os
import sys

from gateway.settings import settings


def build(existing: dict) -> dict:
    cfg = dict(existing)
    instances = dict(cfg.get("instances") or {})
    instances[settings.instance_id] = {
        "driver": "openai-compat",
        "displayName": "Qwen (vLLM)",
        "icon": {"kind": "preset", "preset": "qwen"},
        "environment": {"VLLM_API_KEY": settings.llm_api_key or "EMPTY"},
        "config": {"url": settings.llm_base_url, "apiKeyEnv": "VLLM_API_KEY", "model": settings.llm_model},
    }
    cfg["instances"] = instances

    if settings.decider_base_url:
        cfg["decider"] = {
            "enabled": True,
            "provider": "openrouter",
            "openrouterKey": settings.decider_api_key or "EMPTY",
            "openrouterModel": settings.decider_model,
            "openrouterApi": "chat",
            "openrouterBaseUrl": settings.decider_base_url,
            "jobs": {"roomRouting": True},
        }
    else:
        cfg["decider"] = {**(cfg.get("decider") or {}), "provider": "off", "enabled": False}

    backend = settings.backend_url.rstrip("/")
    servers = dict(cfg.get("mcpServers") or {})
    servers["fin_user"] = {"type": "http", "url": f"{backend}/mcp/user/", "enabled": True,
                           "headers": {"Authorization": f"Bearer {settings.mcp_user_token}"}}
    servers["fin_market"] = {"type": "http", "url": f"{backend}/mcp/market/", "enabled": True,
                             "headers": {"Authorization": f"Bearer {settings.mcp_market_token}"}}
    cfg["mcpServers"] = servers

    features = dict(cfg.get("features") or {})
    # Per-user bots learn from their own private room; shared bots never join rooms.
    features["roomMemoryCapture"] = True
    cfg["features"] = features
    # Nobody answers approval cards on a headless server.
    cfg.setdefault("loopGuard", {"enabled": True})
    return cfg


def main() -> None:
    data_dir = settings.omb_data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "config.json"
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            print(f"config_init: {path} is not valid JSON, rewriting", file=sys.stderr)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(build(existing), indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    print(f"config_init: wrote {path}")


if __name__ == "__main__":
    main()
