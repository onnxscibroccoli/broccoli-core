#!/usr/bin/env python3
"""Search repo for RISH/Termux notification send & recv."""
import json, re, time
from pathlib import Path

BRO = Path.home() / "broccoli"
REPORT_JSON = BRO / "reports/notif_codebase_search.json"
REPORT_TXT = BRO / "reports/notif_codebase_search.txt"

def roots():
    r = [BRO, Path("/sdcard/Broccoli"), Path("/sdcard/Broccoli/pull")]
    pull = Path("/sdcard/Broccoli/pull")
    if pull.exists():
        for b in pull.glob("bundle_*"):
            for sub in (b / "broccoli", b):
                if sub.exists():
                    r.append(sub)
    out, seen = [], set()
    for p in r:
        if p.exists():
            s = str(p.resolve())
            if s not in seen:
                seen.add(s)
                out.append(p)
    return out

PATTERNS = [
    ("termux_send", r"termux-notification\b"),
    ("termux_recv", r"termux-notification-list\b"),
    ("termux_send", r"--button\d(-action)?\b"),
    ("termux_send", r"--ongoing\b|--action\b"),
    ("rish", r"RISH_APPLICATION_ID|RUN_COMMAND|broccoli_rish"),
    ("nls", r"NotificationListenerService|onNotificationPosted"),
    ("broccoli", r"broccoli_notif|recv_notif|status_notify"),
]
compiled = [(c, re.compile(rx, re.I)) for c, rx in PATTERNS]
EXT = {".py", ".sh", ".md", ".txt", ".json", ".java", ".kt", ".xml", ""}
SKIP = {".git", "__pycache__", "node_modules"}

hits_by_file = []
for root in roots():
    for p in root.rglob("*"):
        if not p.is_file() or any(x in p.parts for x in SKIP):
            continue
        if p.suffix not in EXT and "bin" not in p.parts:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")[:500_000]
        except Exception:
            continue
        hits = []
        for i, line in enumerate(t.splitlines(), 1):
            for cat, rx in compiled:
                if rx.search(line):
                    hits.append({"cat": cat, "line": i, "text": line.strip()[:200]})
        if hits:
            hits_by_file.append({"path": str(p), "hits": hits[:30], "n": len(hits)})

hits_by_file.sort(key=lambda x: -x["n"])
data = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "files": len(hits_by_file), "top": hits_by_file[:60]}
REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
lines = [f"SEARCH @ {data['ts']}  files={data['files']}", ""]
for f in hits_by_file[:25]:
    lines.append(f"{f['n']:3d}  {f['path']}")
    for h in f["hits"][:2]:
        lines.append(f"      L{h['line']} [{h['cat']}] {h['text'][:100]}")
REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(REPORT_TXT.read_text(encoding="utf-8"))
print("JSON:", REPORT_JSON)
