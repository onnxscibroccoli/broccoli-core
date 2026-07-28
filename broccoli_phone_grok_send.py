#!/usr/bin/env python3
import argparse, os, subprocess, sys
from pathlib import Path
B = Path(os.environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
def run(a, t=120):
    return subprocess.run(a, cwd=str(B), env={**os.environ,"BROCCOLI_DIR":str(B)}, timeout=t).returncode
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--ping", action="store_true")
    a = ap.parse_args()
    for s in ("go_to_grok_chat.sh","ensure_grok_window.sh"):
        p = B/s
        if p.is_file() and run(["bash",str(p)],90)==0: break
    else: print("no launch",file=sys.stderr); return 2
    if a.ping and (B/"report_to_grok.sh").is_file(): return run(["bash",str(B/"report_to_grok.sh")],180)
    if a.send:
        if not (B/"outbox_context.txt").is_file() or (B/"outbox_context.txt").stat().st_size==0:
            run(["python3",str(B/"broccoli_host.py"),"--build-outbox-only"],60)
        return run(["bash",str(B/"chat_inject.sh")],120)
    run(["bash",str(B/"ui_pull.sh")],30); subprocess.run(["python3",str(B/"screen_state.py")],cwd=str(B))
    print("grok_launch_ok"); return 0
if __name__=="__main__": raise SystemExit(main())
