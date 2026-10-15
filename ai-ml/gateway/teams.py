"""Agent catalog -> OpenMausBot team files -> `openmausbot team apply`.

Agents are created on first start (like a migration) and only re-applied when the inputs
that define them change: their SOUL.md files, the model, or (for watchers) the clusters.
`team apply` itself is idempotent, the hash just avoids spawning it needlessly.

Shared teams (desks) are not user specific and keep their own OMB memory.
Per-user teams are cloned from the same SOUL.md files for each person; their only
memory is their private room, so nothing can leak between users.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

import yaml

from gateway.settings import settings

log = logging.getLogger(__name__)
CATALOG_VERSION = "4"

# Small models drown in tool schemas (OMB offers ~70 by default), so every bot gets an allow-list:
# its own MCP server, its notes, and nothing that can create bots, rooms or reach other conversations.
MEMORY_TOOLS = ("native:*", "mcp:agents:memory_update", "mcp:agents:memory_log", "mcp:agents:session_search")
USER_TOOLS = (*MEMORY_TOOLS, "mcp:fin_user:*")
DESK_TOOLS = (*MEMORY_TOOLS, "mcp:fin_market:*")
LEAD_TOOLS = (*DESK_TOOLS, "mcp:agents:coordinate_bots", "mcp:agents:assignment_status", "mcp:agents:tool_result_read")
BROWSER_TOOLS = ("mcp:browser:*",)

ASSET_DESKS = [
    # asset class slug, team name, bot name prefix
    ("gold_silver", "Bullion Desk", "Bullion"),
    ("psx", "PSX Desk", "PSX"),
    ("foreign_stocks", "Global Equities Desk", "Global Equities"),
    ("crypto", "Crypto Desk", "Crypto"),
    ("pk_real_estate", "Real Estate Desk", "Real Estate"),
]

USER_BOTS = [
    # role, prompt dir, title, description
    ("assistant", "finance_assistant", "Finance Assistant",
     "Leads the chat: onboarding, updates to money, goals, banks and cards, everyday questions."),
    ("savings", "savings_advisor", "Savings Coach",
     "Studies spending habits, budgets, sadqah and motivation; protects the savings plan."),
    ("deals", "deals_advisor", "Deals Advisor",
     "Finds discounts the person can use with their cards at places they like."),
    ("investment", "investment_advisor", "Investment Advisor",
     "Optional. Explains signals and research from the investment desks, with disclaimers."),
]


@dataclass
class BotSpec:
    name: str
    team: str
    kind: str
    title: str
    description: str
    soul: str
    chief: bool = False
    browser: bool = False
    allow: tuple[str, ...] = ()


class ApplyError(RuntimeError):
    pass


def soul(prompt_dir: str) -> str:
    path = settings.prompts_dir / prompt_dir / "SOUL.md"
    if not path.exists():
        raise ApplyError(f"missing prompt {path}")
    return path.read_text(encoding="utf-8").strip() + "\n"


def model_ref() -> str:
    return f"{settings.instance_id}/{settings.llm_model}"


def _hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode())
        h.update(b"\0")
    return h.hexdigest()


# ---------------------------------------------------------------------------- shared desks

def shared_bots(clusters: list[dict]) -> list[BotSpec]:
    browse = settings.llm_supports_vision
    bots: list[BotSpec] = []
    def tools(lead: bool = False, browser: bool = False) -> tuple[str, ...]:
        return (*(LEAD_TOOLS if lead else DESK_TOOLS), *(BROWSER_TOOLS if browser and browse else ()))
    for slug, team, prefix in ASSET_DESKS:
        bots.append(BotSpec(f"{prefix} Researcher", team, "researcher", f"{prefix} researcher",
                            f"Gathers credible news and data on {prefix.lower()} and saves research notes.",
                            soul(f"{slug}_researcher"), browser=browse, allow=tools(browser=True)))
        bots.append(BotSpec(f"{prefix} Analyst", team, "analyst", f"{prefix} expert analyst",
                            f"Turns research and watcher signals into expert analysis for {prefix.lower()}.",
                            soul(f"{slug}_analyst"), chief=True, allow=tools(lead=True)))
        watcher = soul(f"{slug}_watcher")
        for c in clusters:
            if c["asset_class"] != slug:
                continue
            text = (watcher + f"\n## Your cluster\n- cluster_slug: `{c['slug']}`\n- name: {c['name']}\n"
                    f"- about: {c['description']}\n- Always load the current symbols with get_watchlist(\"{c['slug']}\"); "
                    "the list grows when users ask for new assets.\n")
            bots.append(BotSpec(f"Watcher · {c['name']}", team, "watcher", f"Watcher for {c['name']}",
                                f"Watches {', '.join(c['symbols'][:8])} and emits signals.", text, allow=tools()))
    team = "Deals Desk"
    bots.append(BotSpec("Deals Source Scout", team, "deals_scout", "Finds where merchants publish deals",
                        "Finds official websites, deal pages and social media accounts of Pakistani merchants.",
                        soul("deals_source_scout"), browser=browse, allow=tools(browser=True)))
    bots.append(BotSpec("Deals Crawler", team, "deals_crawler", "Collects current deals",
                        "Reads merchant and bank sources and saves structured deals.",
                        soul("deals_crawler"), browser=browse, allow=tools(browser=True)))
    bots.append(BotSpec("Deals Curator", team, "deals_curator", "Keeps the deals database clean",
                        "Expires, de-duplicates and verifies deals.", soul("deals_curator"), chief=True, allow=tools(lead=True)))
    return bots


def shared_team_doc(bots: list[BotSpec]) -> dict:
    teams = {}
    for _slug, team, _prefix in ASSET_DESKS:
        teams[team] = (f"The {team} serves a Pakistani personal-finance app. You never talk to end users and never "
                       f"see their data. Your output goes into the shared database through the fin_market tools, "
                       f"where each user's private Investment Advisor reads it. Be factual, cite sources, and "
                       f"prefer Pakistani context (PKR, SBP, PSX, SECP).")
    teams["Deals Desk"] = ("The Deals Desk keeps a database of every deal and discount in Pakistan: who offers it, "
                           "until when, whether it needs a specific bank card, the city and the type of place. "
                           "Users' private Deals Advisors read it through their own tools. Only save deals you "
                           "actually saw on a source page.")
    return _doc(bots, teams, prune=True)


# ---------------------------------------------------------------------------- per-user teams

def user_short(user_id: str) -> str:
    return user_id.replace("-", "")[:10]


def user_names(user_id: str) -> dict[str, str]:
    short = user_short(user_id)
    return {role: f"{title} · {short}" for role, _, title, _ in USER_BOTS} | {"room": f"Bachat · {short}",
                                                                              "team": f"User {short}"}


def user_soul_version() -> str:
    return _hash(CATALOG_VERSION, model_ref(), *[soul(p) for _, p, _, _ in USER_BOTS])


def user_team_doc(user_id: str, display_name: str, bulletin: str, investment: bool) -> tuple[dict, dict]:
    names = user_names(user_id)
    team = names["team"]
    bots = []
    for role, prompt, title, desc in USER_BOTS:
        if role == "investment" and not investment:
            continue
        bots.append(BotSpec(names[role], team, f"user_{role}", title, desc, soul(prompt),
                            chief=role == "assistant", allow=USER_TOOLS))
    brief = (f"Private team serving one person ({display_name}). The room bulletin holds their member_key. "
             "Work only from that person's data via fin_user tools.")
    doc = _doc(bots, {team: brief}, prune=True)
    doc["rooms"] = [{
        "name": names["room"], "team": team, "members": [b.name for b in bots], "brief": bulletin,
        "responder": names["assistant"],
    }]
    roster = {role: {"name": names[role], "label": title} for role, _, title, _ in USER_BOTS
              if role != "investment" or investment}
    return doc, roster


# ---------------------------------------------------------------------------- yaml + apply

def _doc(bots: list[BotSpec], teams: dict[str, str], prune: bool) -> dict:
    return {
        "version": 1,
        "defaults": {"model": model_ref(), "approval": "full", "computer": "off", "browser": False},
        "teams": [{"name": name, "brief": brief, "prune": prune} for name, brief in teams.items()],
        "bots": [_bot_yaml(b) for b in bots],
    }


def _bot_yaml(b: BotSpec) -> dict:
    out = {"name": b.name, "team": b.team, "title": b.title[:200], "description": b.description, "soul": b.soul}
    if b.chief:
        out["chief"] = True
    if b.browser:
        out["computer"] = "browser"
        out["browser"] = {"enabled": True, "profile": "guest"}
    if b.allow:
        out["tools"] = {"allow": list(b.allow)}
    return out


_apply_lock = asyncio.Lock()


async def apply(doc: dict, label: str) -> dict:
    """Run `openmausbot team apply` for one file. Serialised: OMB applies one team at a time."""
    folder = settings.gateway_state_dir / "teams"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{re.sub(r'[^a-zA-Z0-9_-]+', '-', label)}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    args = [*shlex.split(settings.omb_cli), "team", "apply", str(path), "--json", "--quiet", "--wait-idle", "60s"]
    if any(t.get("prune") for t in doc.get("teams", [])):
        args.append("--prune")
    env = {**os.environ, "OMB_PORT": settings.omb_url.rsplit(":", 1)[-1]}
    async with _apply_lock:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE, env=env, cwd=str(folder))
        out, err = await asyncio.wait_for(proc.communicate(), timeout=600)
    text = out.decode(errors="replace").strip()
    try:
        result = json.loads(text) if text else {}
    except json.JSONDecodeError:
        result = {"raw": text[-2000:]}
    if proc.returncode != 0:
        raise ApplyError(f"team apply {label} exited {proc.returncode}: {(result.get('error') or text or err.decode())[:800]}")
    return result


class SyncState:
    """Remembers the input hash of each applied team file."""

    def __init__(self) -> None:
        self.path: Path = settings.gateway_state_dir / "sync-state.json"
        self.data: dict = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.data = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))


def shared_hash(doc: dict) -> str:
    return _hash(CATALOG_VERSION, json.dumps(doc, sort_keys=True))
