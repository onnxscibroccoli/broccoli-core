#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
OUT="$HOME/broccoli/reports/INVENTORY_REPORT.md"
JSON="$HOME/broccoli/reports/inventory.json"
LOG="$HOME/broccoli/reports/inventory.log"

ROOTS=(
  "$HOME/broccoli"
  "$HOME"
)

log(){ echo "$(date -Iseconds) $*" >> "$LOG"; }
log "inventory start"

python3 <<'PY'
import json, os, re
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
roots = [HOME / "broccoli", HOME]
# skip huge dirs
SKIP = {".git", "__pycache__", "node_modules", ".cache", "usr", "lib", "include"}

def walk_md(root: Path):
    if not root.is_dir():
        return
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".")]
        # don't walk entire $HOME deeply except broccoli
        if root == HOME and "broccoli" not in dp and dp != str(HOME):
            if dp != str(HOME / "broccoli"):
                dns[:] = []
        for fn in fns:
            if fn.lower().endswith(".md"):
                yield Path(dp) / fn

CHECK_DONE = re.compile(
    r"\[x\]|\[X\]|✅|DONE|COMPLETE|TASK_COMPLETE|FINISHED|PASS\b|_OK\b|wire PASS|AGENT_.*_ON",
    re.I,
)
CHECK_TODO = re.compile(
    r"\[ \]|TODO|FIXME|WIP|PENDING|Fix:|MED\]|HIGH\]|CRITICAL\]|MANUAL|fail",
    re.I,
)
HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.M)

md_files = []
for r in roots:
    for p in walk_md(r):
        try:
            rel = str(p.relative_to(HOME))
        except ValueError:
            rel = str(p)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        st = p.stat()
        done_hits = len(CHECK_DONE.findall(text))
        todo_hits = len(CHECK_TODO.findall(text))
        headings = [m.group(2).strip()[:80] for m in HEADING.finditer(text)][:15]
        tasks = []
        for line in text.splitlines():
            line = line.strip()
            if re.match(r"^[-*]\s+\[[ xX]\]", line):
                tasks.append(line[:200])
            elif line.startswith("ASK|") or "task_box" in str(p):
                if len(line) < 300:
                    tasks.append(line[:200])
        md_files.append({
            "path": rel,
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "done_signals": done_hits,
            "todo_signals": todo_hits,
            "headings": headings,
            "task_lines": tasks[:20],
            "preview": text[:400].replace("\n", " "),
        })

md_files.sort(key=lambda x: x["path"])

# Runtime task state (not only md)
runtime = {}
B = HOME / "broccoli"
for key, sub in [
    ("queue_pending", "queue/pending.txt"),
    ("queue_done", "queue/done.txt"),
    ("task_box", "task_box.txt"),
    ("agent_iteration", "meta/agent_iteration.json"),
    ("agent_state", "meta/agent_state.json"),
    ("heal_state", "meta/heal_state.json"),
    ("grok_last", "thread/grok_last.txt"),
    ("to_chat", "thread/to_chat.md"),
    ("investigation", "reports/INVESTIGATION_REPORT.md"),
    ("instructions", "INSTRUCTIONS.md"),
    ("context_prompt", "CONTEXT_PROMPT.md"),
]:
    p = B / sub
    if p.is_file():
        runtime[key] = {"exists": True, "bytes": p.stat().st_size}
        if sub.endswith(".txt") or sub.endswith(".md"):
            runtime[key]["head"] = p.read_text(errors="replace").splitlines()[:8]
        if sub.endswith(".json"):
            try:
                runtime[key]["json"] = json.loads(p.read_text())
            except Exception:
                pass
    else:
        runtime[key] = {"exists": False}

# Script capabilities inventory
tools = sorted((B / "tools").glob("*.sh")) if (B / "tools").is_dir() else []
libs = sorted((B / "lib").glob("*.sh")) if (B / "lib").is_dir() else []
pytools = sorted((B / "tools").glob("*.py")) if (B / "tools").is_dir() else []

daemons = {}
import subprocess
for name, pat in [
    ("agent_daemon", "broccoli/tools/agent_daemon.sh"),
    ("heal_supervisor", "broccoli/tools/heal_supervisor.sh"),
    ("notify_watch", "broccoli/tools/notify_watch.sh"),
    ("wire_daemon", "broccoli/tools/wire_daemon.sh"),
]:
    try:
        r = subprocess.run(["pgrep", "-af", pat], capture_output=True, text=True, timeout=5)
        daemons[name] = r.stdout.strip() or "(not running)"
    except Exception:
        daemons[name] = "?"

report = {
    "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "md_count": len(md_files),
    "md_files": md_files,
    "runtime": runtime,
    "daemons": daemons,
    "tools_sh": [str(t.relative_to(HOME)) for t in tools],
    "lib_sh": [str(t.relative_to(HOME)) for t in libs],
    "tools_py": [str(t.relative_to(HOME)) for t in pytools],
}

out_md = HOME / "broccoli/reports/INVENTORY_REPORT.md"
lines = [
    "# Broccoli inventory & task status",
    f"Generated: {report['ts']}",
    "",
    "## Daemons (live)",
]
for k, v in daemons.items():
    lines.append(f"- **{k}**: 
