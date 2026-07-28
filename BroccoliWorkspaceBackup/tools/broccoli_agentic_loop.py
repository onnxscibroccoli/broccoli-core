#!/usr/bin/env python3
import os, sys, time, json, subprocess
from pathlib import Path
BRO = Path.home() / "broccoli"
sys.path.insert(0, str(BRO/"lib"))
os.environ.setdefault("BROCCOLI_PROGRAMMATIC", "1")
from broccoli_agentic_chat import send_prompt_agentic, stopped, log
POLL = float(os.environ.get("BROCCOLI_POLL_SEC", "10"))
while not stopped():
    p = BRO/"inbox/prompt.txt"
    prompt = p.read_text(encoding="utf-8").strip() if p.exists() and p.stat().st_size else "BROCC_FAST reply LOOP_OK"
    r = send_prompt_agentic(prompt)
    log("LOOP " + json.dumps({k: r.get(k) for k in ("ok","via","error","partial")})[:500])
    if os.system("command -v brocc >/dev/null") == 0:
        subprocess.run(["brocc","agent-loop-once"], cwd=str(BRO), timeout=40)
    te = time.time() + POLL
    while time.time() < te and not stopped():
        time.sleep(0.2)
