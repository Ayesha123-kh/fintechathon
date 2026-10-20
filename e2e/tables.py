"""results/*.json -> markdown tables (one per section) for the report appendix, plus totals."""
import json, sys
from collections import Counter, OrderedDict
from pathlib import Path

ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️", "INFO": "ℹ️"}
res = Path(sys.argv[1])
for name, title in (("api", "Scripted API journeys"), ("chat_actions", "Changing things by chatting"),
                    ("ingest", "Bank-alert email parsing"), ("browser", "Browser journeys (headless Chrome)")):
    f = res / f"{name}.json"
    if not f.exists():
        continue
    rows = json.loads(f.read_text())
    c = Counter(r["status"] for r in rows)
    print(f"\n### {title} · " + ", ".join(f"{c[k]} {k.lower()}" for k in ("PASS", "WARN", "FAIL", "INFO") if c[k]) + "\n")
    secs = OrderedDict()
    for r in rows:
        secs.setdefault(r["section"], []).append(r)
    for sec, items in secs.items():
        print(f"<details><summary><b>{sec}</b> ({sum(1 for i in items if i['status']=='PASS')}/{len(items)} passed)</summary>\n")
        print("| | Check | Detail |\n|---|---|---|")
        for i in items:
            d = i["detail"].replace("|", "\\|").replace("\\n", " ").replace("\n", " ")[:160] if i["status"] != "PASS" or any(
                k in i["name"] for k in ("voice", "reply", "Assistant replied", "replies", "loads (", "lands on")) else ""
            print(f"| {ICON[i['status']]} | {i['name'].replace('|', '/')} | {d} |")
        print("\n</details>\n")
