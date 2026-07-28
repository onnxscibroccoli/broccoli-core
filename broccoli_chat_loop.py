#!/usr/bin/env python3
"""Unattended: Termux background only; each step launches Grok via Rish."""
import os, subprocess, sys, time
from pathlib import Path

BROCCOLI_DIR = Path(os.environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
sys.path.insert(0, str(BROCCOLI_DIR))
import chat_scraper

def log(m):
    line = f"[{time.strftime('%F %T')}] {m}\n"
    (BROCCOLI_DIR / "chat_loop.log").open("a", encoding="utf-8").write(line)
    print(line, end="", flush=True)

def one_cycle(wait_sec=900, poll=4.0):
    host = BROCCOLI_DIR / "broccoli_host.py"
    subprocess.run([sys.executable, str(host), "--build-outbox-only"], cwd=str(BROCCOLI_DIR), timeout=120)
    subprocess.run(["bash", str(BROCCOLI_DIR / "chat_inject.sh")], cwd=str(BROCCOLI_DIR), timeout=180)
    chat_scraper.set_baseline_after_inject()
    log("Grok launched + outbox sent; polling Copy chip until new agent reply...")
    r = chat_scraper.wait_for_new_response(wait_sec, poll)
    if not r.extracted_agent_block:
        log(r.error or "no agent block"); return "error"
    if not chat_scraper.write_inbox(r):
        return "error"
    log("inbox from clipboard (Copy chip)")
    subprocess.run([sys.executable, str(host), "--execute-inbox-only"], cwd=str(BROCCOLI_DIR), timeout=600)
    t = (BROCCOLI_DIR / "inbox_response.txt").read_text(encoding="utf-8", errors="replace").strip()
    return "complete" if t.startswith("TASK_COMPLETE:") else "continue"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cycles", type=int, default=100)
    ap.add_argument("--wait-sec", type=float, default=900)
    ap.add_argument("--poll", type=float, default=4.0)
    args = ap.parse_args()
    log("Broccoli loop started (Termux may stay background; Grok brought forward automatically)")
    for i in range(args.max_cycles):
        log(f"cycle {i+1}")
        st = one_cycle(args.wait_sec, args.poll)
        if st == "complete":
            log("TASK_COMPLETE"); return 0
        if st == "error":
            time.sleep(8)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
