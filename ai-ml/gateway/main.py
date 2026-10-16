"""Gateway between the backend and OpenMausBot.

Runs next to OMB (same container / network namespace) so it talks to OMB over loopback,
and is the only service the backend calls. Responsibilities:
  * create/update agents from prompts/<agent>/SOUL.md on startup (only when changed)
  * provision a private team + group chat per user
  * forward user messages into rooms and relay bot replies back
  * wake shared bots on the backend scheduler's request
"""

import asyncio
import logging
import secrets
from datetime import UTC, datetime

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from gateway import teams
from gateway.omb import OMBError, omb
from gateway.relay import relay
from gateway.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("gateway")

state = teams.SyncState()
status_info: dict = {"started_at": datetime.now(UTC).isoformat(), "last_sync": None, "last_sync_error": None}
_user_locks: dict[str, asyncio.Lock] = {}


def internal(x_internal_key: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(401, "bad_internal_key")


async def backend(method: str, path: str, json=None):
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=60,
                                 headers={"x-internal-key": settings.internal_api_key}) as c:
        r = await c.request(method, f"/api/internal{path}", json=json)
        r.raise_for_status()
        return r.json()


# ------------------------------------------------------------------------- sync

async def sync_shared(force: bool = False) -> dict:
    clusters = await backend("GET", "/clusters")
    bots = teams.shared_bots(clusters)
    doc = teams.shared_team_doc(bots)
    digest = teams.shared_hash(doc)
    applied = False
    if force or state.get("shared") != digest:
        log.info("applying shared desks (%d bots)", len(bots))
        await teams.apply(doc, "shared-desks")
        state.set("shared", digest)
        applied = True
    snap = await omb.snapshot()
    ids = {b["name"]: b["id"] for b in snap.get("bots", [])}
    await backend("POST", "/agents/registry", [
        {"name": b.name, "team": _desk_key(b), "kind": b.kind, "soul_hash": teams._hash(b.soul),
         "omb_bot_id": ids.get(b.name), "status": "ok" if b.name in ids else "missing"} for b in bots
    ])
    return {"applied": applied, "bots": len(bots)}


def _desk_key(b: teams.BotSpec) -> str:
    for slug, team, _ in teams.ASSET_DESKS:
        if b.team == team:
            return slug
    return "deals"


async def apply_user(user_id: str, display_name: str, bulletin: str, investment: bool) -> dict:
    lock = _user_locks.setdefault(teams.user_short(user_id), asyncio.Lock())
    async with lock:
        doc, roster = teams.user_team_doc(user_id, display_name, bulletin, investment)
        await teams.apply(doc, f"user-{teams.user_short(user_id)}")
        names = teams.user_names(user_id)
        snap = await omb.snapshot()
        room = next((g for g in snap.get("groups", []) if g.get("name") == names["room"]), None)
        if not room:
            raise OMBError("room was not created")
        ids = {b["name"]: b["id"] for b in snap.get("bots", [])}
        bots = {role: {**info, "id": ids.get(info["name"])} for role, info in roster.items()}
        if settings.decider_base_url:
            try:  # let the decision model pick who answers each message
                await omb.request("PATCH", f"/api/groups/{room['id']}", json={"defaultResponder": {"kind": "auto"}})
            except OMBError as exc:
                log.info("auto responder not set for %s: %s", names["room"], exc)
        relay.watch_thread(room["threadId"])
        return {"room_id": room["id"], "thread_id": room["threadId"], "bots": bots,
                "soul_version": teams.user_soul_version()}


async def sync_users() -> int:
    """Re-apply per-user teams whose SOUL files changed since they were created."""
    version = teams.user_soul_version()
    updated = 0
    for u in await backend("GET", "/agents/users"):
        if u.get("soul_version") == version:
            continue
        try:
            result = await apply_user(u["user_id"], u["display_name"], u["bulletin"], u["investment"])
            await backend("POST", "/agents/users/soul-version",
                          {"user_id": u["user_id"], "soul_version": version, "bots": result["bots"]})
            updated += 1
        except Exception as exc:
            log.warning("user team %s not updated: %s", u["user_id"], exc)
    return updated


async def deprovision(short: str) -> dict:
    """Remove one person's private room, bots and team from OpenMausBot."""
    removed = {"room": False, "bots": 0, "team": False}
    lock = _user_locks.setdefault(short, asyncio.Lock())
    async with lock:
        snap = await omb.snapshot()
        for g in snap.get("groups", []):
            if g.get("name") == f"Bachat · {short}":
                relay.room_threads.discard(g.get("threadId"))
                try:  # a room that is mid-turn refuses deletion, so stop it first
                    await omb.request("POST", f"/api/groups/{g['id']}/interrupt", json={})
                except OMBError:
                    pass
                await omb.request("DELETE", f"/api/groups/{g['id']}")
                removed["room"] = True
        for b in snap.get("bots", []):
            if str(b.get("name", "")).endswith(f" · {short}") and not str(b.get("name")).startswith("Watcher"):
                try:
                    await omb.request("POST", f"/api/bots/{b['id']}/interrupt", json={})
                except OMBError:
                    pass
                await omb.request("DELETE", f"/api/bots/{b['id']}")
                removed["bots"] += 1
        if f"User {short}" in snap.get("sections", []):
            await omb.request("DELETE", "/api/sidebar-sections", params={"section": f"User {short}"})
            removed["team"] = True
    (settings.gateway_state_dir / "teams" / f"user-{short}.yaml").unlink(missing_ok=True)
    _user_locks.pop(short, None)
    log.info("deprovisioned user team %s: %s", short, removed)
    return removed


async def remove_orphans() -> int:
    """Delete per-user teams whose person no longer exists (deleted by an admin, or directly in SQL)."""
    known = {teams.user_short(uid) for uid in await backend("GET", "/agents/known-users")}
    snap = await omb.snapshot()
    present = {sec.removeprefix("User ") for sec in snap.get("sections", []) if sec.startswith("User ")}
    present |= {g["name"].removeprefix("Bachat · ") for g in snap.get("groups", [])
                if str(g.get("name", "")).startswith("Bachat · ")}
    orphans = present - known
    for short in orphans:
        try:
            await deprovision(short)
        except OMBError as exc:
            log.warning("could not remove orphaned team %s: %s", short, exc)
    return len(orphans)


async def startup_sync() -> None:
    for attempt in range(30):
        try:
            await omb.wait_ready()
            await omb.ensure_token()
            shared = await sync_shared()
            users = await sync_users()
            orphans = await remove_orphans()
            status_info.update(last_sync=datetime.now(UTC).isoformat(), last_sync_error=None,
                               shared=shared, users_updated=users, orphans_removed=orphans)
            log.info("startup sync done: %s, %d user teams updated, %d orphans removed", shared, users, orphans)
            return
        except Exception as exc:
            status_info["last_sync_error"] = str(exc)[:500]
            log.warning("startup sync attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(min(60, 5 * (attempt + 1)))


app = FastAPI(title="Agents gateway")


@app.on_event("startup")
async def on_startup() -> None:
    asyncio.get_running_loop().create_task(startup_sync())
    asyncio.get_running_loop().create_task(relay.run())
    asyncio.get_running_loop().create_task(relay.flusher())


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/status", dependencies=[Depends(internal)])
async def status() -> dict:
    try:
        snap = await omb.snapshot()
        bots = [{"name": b.get("name"), "id": b.get("id"), "status": b.get("status"),
                 "working": bool(b.get("working") or b.get("busy"))} for b in snap.get("bots", [])]
        omb_ok = True
    except Exception as exc:
        bots, omb_ok = [], False
        status_info["omb_error"] = str(exc)[:300]
    return {**status_info, "ok": omb_ok, "relay_connected": relay.connected, "rooms_watched": len(relay.room_threads),
            "bot_count": len(bots), "user_soul_version": teams.user_soul_version()[:12],
            "shared_bots": [b for b in bots if not b["name"] or "·" not in b["name"] or b["name"].startswith("Watcher")]}


@app.get("/usage", dependencies=[Depends(internal)])
async def usage() -> dict:
    return await omb.request("GET", "/api/usage", params={"groupBy": "bot"})


@app.post("/sync", dependencies=[Depends(internal)])
async def force_sync() -> dict:
    shared = await sync_shared(force=True)
    users = await sync_users()
    orphans = await remove_orphans()
    status_info.update(last_sync=datetime.now(UTC).isoformat(), last_sync_error=None)
    return {"shared": shared, "users_updated": users, "orphans_removed": orphans}


class DeprovisionIn(BaseModel):
    user_id: str


@app.post("/users/deprovision", dependencies=[Depends(internal)])
async def deprovision_user(body: DeprovisionIn) -> dict:
    try:
        return await deprovision(teams.user_short(body.user_id))
    except OMBError as exc:
        raise HTTPException(502, str(exc)) from exc


class ProvisionIn(BaseModel):
    user_id: str
    display_name: str
    bulletin: str
    investment: bool = False


@app.post("/users/provision", dependencies=[Depends(internal)])
async def provision(body: ProvisionIn) -> dict:
    try:
        return await apply_user(body.user_id, body.display_name, body.bulletin, body.investment)
    except (OMBError, teams.ApplyError) as exc:
        raise HTTPException(502, str(exc)) from exc


class UpdateIn(BaseModel):
    user_id: str
    room_id: str | None = None
    bulletin: str
    investment: bool = False
    display_name: str = ""


async def _apply_with_retries(body: UpdateIn) -> None:
    # Usually called from inside a bot's own turn (a tool changed the profile), and OMB refuses
    # room changes while the room is working, so retry until the turn has finished.
    for attempt in range(6):
        try:
            result = await apply_user(body.user_id, body.display_name or "this person", body.bulletin, body.investment)
            await backend("POST", "/agents/users/soul-version",
                          {"user_id": body.user_id, "soul_version": result["soul_version"], "bots": result["bots"]})
            return
        except Exception as exc:
            log.info("update of %s deferred (attempt %d): %s", body.user_id, attempt + 1, exc)
            await asyncio.sleep(20 * (attempt + 1))
    log.warning("giving up updating user team %s", body.user_id)


@app.post("/users/update", dependencies=[Depends(internal)])
async def update_user(body: UpdateIn) -> dict:
    _, roster = teams.user_team_doc(body.user_id, body.display_name or "this person", body.bulletin, body.investment)
    asyncio.get_running_loop().create_task(_apply_with_retries(body))
    return {"accepted": True, "bots": roster}


class MessageIn(BaseModel):
    user_id: str
    room_id: str
    text: str
    send_id: str | None = None


@app.post("/users/message", dependencies=[Depends(internal)])
async def message(body: MessageIn) -> dict:
    payload = {"text": body.text}
    if body.send_id:
        payload["sendId"] = body.send_id
    try:
        return await omb.request("POST", f"/api/groups/{body.room_id}/messages", json=payload)
    except OMBError as exc:
        raise HTTPException(502, str(exc)) from exc


class TriggerIn(BaseModel):
    bot: str
    text: str


@app.post("/bots/trigger", dependencies=[Depends(internal)])
async def trigger(body: TriggerIn) -> dict:
    bot = await omb.bot_by_name(body.bot)
    if not bot:
        raise HTTPException(404, f"no bot named {body.bot}")
    try:
        await omb.request("POST", f"/api/bots/{bot['id']}/messages", json={"text": body.text})
    except OMBError as exc:
        # 409 = still working on the previous job; skipping this cycle is fine.
        raise HTTPException(409 if "409" in str(exc) else 502, str(exc)) from exc
    return {"ok": True, "bot_id": bot["id"]}
