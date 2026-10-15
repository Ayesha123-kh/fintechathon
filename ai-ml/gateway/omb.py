"""Thin OpenMausBot HTTP client. Obtains an admin session token through loopback pairing."""

import asyncio
import logging

import httpx

from gateway.settings import settings

log = logging.getLogger(__name__)


class OMBError(RuntimeError):
    pass


class OMB:
    def __init__(self) -> None:
        self.token: str | None = None
        self._token_file = settings.gateway_state_dir / "omb-token-v2"
        self._lock = asyncio.Lock()

    async def wait_ready(self, timeout: float = 300) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        async with httpx.AsyncClient(timeout=5) as c:
            while True:
                try:
                    r = await c.get(f"{settings.omb_url}/api/health")
                    if r.status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                if asyncio.get_running_loop().time() > deadline:
                    raise OMBError("OpenMausBot did not become healthy")
                await asyncio.sleep(2)

    async def _pair(self) -> str:
        """Loopback is trusted as the owner: open a pairing window and redeem it for a bearer token."""
        async with httpx.AsyncClient(base_url=settings.omb_url, timeout=20) as c:
            r = await c.post("/api/auth/pairing", json={"scopes": ["admin", "client"], "label": "fintech-gateway"})
            if r.status_code >= 400:
                raise OMBError(f"pairing failed: {r.status_code} {r.text[:200]}")
            body = r.json()
            code = body.get("credential") or body["code"]
            r = await c.post("/api/auth/pair", json={"code": code, "label": "fintech-gateway"},
                             headers={"content-type": "application/json"})
            if r.status_code >= 400:
                raise OMBError(f"pair exchange failed: {r.status_code} {r.text[:200]}")
            return r.json()["token"]

    async def ensure_token(self, force: bool = False) -> str:
        async with self._lock:
            if self.token and not force:
                return self.token
            if not force and self._token_file.exists():
                self.token = self._token_file.read_text().strip()
                async with httpx.AsyncClient(base_url=settings.omb_url, timeout=10) as c:
                    r = await c.get("/api/auth/sessions", headers={"Authorization": f"Bearer {self.token}"})
                if r.status_code == 200:
                    return self.token
            self.token = await self._pair()
            settings.gateway_state_dir.mkdir(parents=True, exist_ok=True)
            self._token_file.write_text(self.token)
            self._token_file.chmod(0o600)
            return self.token

    async def request(self, method: str, path: str, json: dict | None = None, params: dict | None = None,
                      timeout: float = 60) -> dict:
        for attempt in range(2):
            token = await self.ensure_token(force=attempt > 0)
            async with httpx.AsyncClient(base_url=settings.omb_url, timeout=timeout) as c:
                r = await c.request(method, path, json=json, params=params,
                                    headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 401 and attempt == 0:
                continue
            if r.status_code >= 400:
                raise OMBError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
            return r.json() if r.content else {}
        raise OMBError("unauthorized")

    async def snapshot(self) -> dict:
        """All bots and rooms (without messages)."""
        return await self.request("GET", "/api/bots", params={"messages": "0"})

    async def bot_by_name(self, name: str) -> dict | None:
        snap = await self.snapshot()
        return next((b for b in snap.get("bots", []) if b.get("name", "").lower() == name.lower()), None)

    async def room_by_name(self, name: str) -> dict | None:
        snap = await self.snapshot()
        return next((g for g in snap.get("groups", []) if g.get("name") == name), None)


omb = OMB()
