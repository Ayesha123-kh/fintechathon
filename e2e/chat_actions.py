"""Chat-first changes, end to end: ask the assistant to create a goal, check the app shows it, then ask it to cancel
the goal and check it's gone. Uses the demo account and the live model; leaves the account as it found it.
Writes results/chat_actions.json."""

import json
import queue
import time

import api_e2e as h

GOAL = "E2E Bicycle"


def ask(c, sse, text: str, timeout: int = 420) -> tuple[dict | None, float, set]:
    t0 = time.time()
    resp = c.post("/api/chat/messages", json={"text": text})
    if resp.status_code != 200:
        return {"role": "error", "text": h.detail(resp)}, 0, set()
    tools, final = set(), None
    while time.time() - t0 < timeout and not final:
        try:
            ev = sse.q.get(timeout=5)
        except queue.Empty:
            continue
        if ev.get("type") == "activity" and ev["activity"].get("tool"):
            tools.add(ev["activity"]["tool"])
        if ev.get("type") == "message" and ev["message"]["role"] in ("bot", "system") and ev["message"]["final"]:
            final = ev["message"]
    return final, time.time() - t0, tools


def goal(c):
    return next((g for g in c.get("/api/goals").json() if GOAL.lower() in g["name"].lower()), None)


def main() -> None:
    h.sec("Changing things by chatting (demo account, live model)")
    c = h.client()
    if not h.check("Demo signs in", h.signin(c, *h.DEMO).status_code == 200):
        return
    if goal(c):
        h.check("No leftover test goal from an earlier run", False, "found one; cancel it first")
        return
    sse = h.SSE(c.cookies)
    sse.connected.wait(15)
    final, took, tools = ask(c, sse, f"Please create a new savings goal called '{GOAL}' for Rs 40,000 with a deadline of "
                                     f"30 June 2027. Just create it, no need to ask me to confirm.")
    g = goal(c)
    if not g and final and "?" in final["text"]:  # the assistant asked to confirm first
        final, more, tools2 = ask(c, sse, "Yes, go ahead and create it.")
        took, tools = took + more, tools | tools2
        g = goal(c)
    h.check(f"Assistant replied to the create request ({took:.0f} s)", bool(final) and final["role"] == "bot",
            (final or {}).get("text", "")[:200])
    h.results[-1]["detail"] = f"{took:.0f}s tools={sorted(tools)}: {(final or {}).get('text', '')[:250]!r}"
    if h.check("The goal really exists afterwards (Goals screen)", bool(g), "not in /api/goals"):
        h.check("…with the target and deadline that were asked for",
                abs(float(g["target"]) - 40000) < 1 and str(g["deadline"]) == "2027-06-30", f"{g['target']} {g['deadline']}")
        d = c.get("/api/dashboard").json()
        h.check("…and it shows on the dashboard", any(GOAL.lower() in x["name"].lower() for x in d["goals"]))
    final, took, tools = ask(c, sse, f"Please cancel the '{GOAL}' goal, I don't need it any more. No need to confirm.")
    if goal(c) and final and "?" in final["text"]:
        final, more, tools2 = ask(c, sse, "Yes, cancel it.")
        took, tools = took + more, tools | tools2
    h.check(f"Assistant replied to the cancel request ({took:.0f} s)", bool(final) and final["role"] == "bot",
            (final or {}).get("text", "")[:200])
    h.results[-1]["detail"] = f"{took:.0f}s tools={sorted(tools)}: {(final or {}).get('text', '')[:250]!r}"
    h.check("The cancelled goal is gone from the Goals screen", goal(c) is None, goal(c))
    sse.stop.set()
    (h.HERE / "results").mkdir(exist_ok=True)
    (h.HERE / "results" / "chat_actions.json").write_text(json.dumps(h.results, indent=1))
    for x in h.results:
        print(x["status"], x["name"], "|", x["detail"][:300])


if __name__ == "__main__":
    main()
