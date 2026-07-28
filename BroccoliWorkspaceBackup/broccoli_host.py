#!/usr/bin/env python3
import json, os, re, subprocess, sys
from pathlib import Path
B = Path(os.environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
OUTBOX, INBOX = B/"outbox_context.txt", B/"inbox_response.txt"
MAX = 12000
def read(p, n=4000):
    return p.read_text(errors="replace")[:n] if p.is_file() else "(empty)"
def build():
    B.mkdir(parents=True, exist_ok=True)
    body = "\n".join(["BROCCOLI_DIR="+str(B), "=== task ===", read(B/"current_task.txt",2000),
        "=== last_output ===", read(B/"last_output.txt",4000), "=== state ===", read(B/"state.json",2000),
        "", "Reply ONE block: CMD:<shell> or TASK_COMPLETE:<text> or WRITE_FILE:<path>\\n<body>\\nEND_WRITE"])
    OUTBOX.write_text(body[:MAX], encoding="utf-8")
def execute():
    raw = INBOX.read_text(encoding="utf-8").strip() if INBOX.is_file() else ""
    if not raw: return 1
    if raw.startswith("TASK_COMPLETE:"):
        s = json.loads((B/"state.json").read_text()) if (B/"state.json").is_file() else {}
        s.update({"phase":"complete"}); (B/"state.json").write_text(json.dumps(s,indent=2)); return 0
    if raw.startswith("CMD:"):
        cmd = raw[4:].strip()
        (B/"last_cmd.txt").write_text(raw+"\n")
        p = subprocess.run(cmd, shell=True, cwd=str(B), capture_output=True, text=True, timeout=600,
            env={**os.environ,"BROCCOLI_DIR":str(B)})
        (B/"last_output.txt").write_text((p.stdout or "")+(p.stderr or "")); return p.returncode
    return 1
if __name__=="__main__":
    if "--build-outbox-only" in sys.argv: build(); print(OUTBOX); raise SystemExit(0)
    if "--execute-inbox-only" in sys.argv: raise SystemExit(execute())
    build()
