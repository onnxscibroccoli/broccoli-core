#!/usr/bin/env python3
import json, os, re, subprocess
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
SKIP = {".git", "__pycache__", "node_modules", ".cache", "usr", "lib", "include"}
CHECK_DONE = re.compile(r"\[x\]|\[X\]|✅|DONE|COMPLETE|PASS\b|_OK\b", re.I)
CHECK_TODO = re.compile(r"\[ \]|TODO|FIXME|WIP|Fix:|CRITICAL\]|HIGH\]|MANUAL|fail", re.I)
HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.M)

def walk_md(root: Path):
    if not root.is_dir():
        return
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".")]
        if root == HOME and "broccoli" not in dp and dp != str(HOME):
            dns[:] = []
        for fn in fns:
            if fn.lower().endswith(".md"):
                yield Path(dp) / fn

md_files = []
for root in [HOME / "broccoli", HOME]:
    for p in walk_md(root):
        try:
            rel = str(p.relative_to(HOME))
        except ValueError:
            rel = str(p)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        st = p.stat()
        tasks = [ln[:200] for ln in text.splitlines() if re.match(r"^[-*]\s+\[[ xX]\]", ln.strip())][:12]
        md_files.append({
            "path": rel, "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "done_signals": len(CHECK_DONE.findall(text)),
            "todo_signals": len(CHECK_TODO.findall(text)),
            "headings": [m.group(2).strip()[:60] for m in HEADING.finditer(text)][:8],
            "task_lines": tasks,
        })
md_files.sort(key=lambda x: x["path"])

B = HOME / "broccoli"
runtime = {}
for key, sub in [
    ("queue_pending", "queue/pending.txt"), ("task_box", "task_box.txt"),
    ("agent_iteration", "meta/agent_iteration.json"),
    ("grok_last", "thread/grok_last.txt"), ("to_chat", "thread/to_chat.md"),
    ("investigation", "reports/INVESTIGATION_REPORT.md"),
    ("instructions", "INSTRUCTIONS.md"),
]:
    p = B / sub
    if p.is_file():
        runtime[key] = {"bytes": p.stat().st_size, "head": p.read_text(errors="replace").splitlines()[:6]}
    else:
        runtime[key] = None

daemons = {}
for name, pat in [
    ("agent_daemon", "broccoli/tools/agent_daemon.sh"),
    ("heal_supervisor", "broccoli/tools/heal_supervisor.sh"),
]:
    try:
        r = subprocess.run(["pgrep", "-af", pat], capture_output=True, text=True, timeout=5)
        daemons[name] = (r.stdout.strip() or "(not running)")[:200]
    except Exception:
        daemons[name] = "?"

report = {
    "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "md_count": len(md_files), "md_files": md_files, "runtime": runtime, "daemons": daemons,
}
out_md = B / "reports/INVENTORY_REPORT.md"
lines = ["# Broccoli inventory", f"Generated: {report['ts']}", "", "## Daemons"]
for k, v in daemons.items():
    lines.append(f"- {k}: {v}")
lines += ["", "## Runtime"]
for k, v in runtime.items():
    lines.append(f"### {k}")
    if not v:
        lines.append("- missing")
        continue
    lines.append(f"- bytes: {v['bytes']}")
    for h in v.get("head", []):
        lines.append(f"  - {h[:100]}")
lines += ["", f"## Markdown ({len(md_files)})", ""]
for m in md_files:
    st = "open" if m["todo_signals"] > m["done_signals"] else ("done" if m["done_signals"] > m["todo_signals"] else "mixed")
    lines.append(f"### {m['path']} [{st}] todo~{m['todo_signals']} done~{m['done_signals']}")
    for t in m.get("task_lines", [])[:4]:
        lines.append(f"  - {t}")
    lines.append("")
(B / "reports/inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
out_md.write_text("\n".join(lines), encoding="utf-8")
print(out_md.read_text(encoding="utf-8"))
