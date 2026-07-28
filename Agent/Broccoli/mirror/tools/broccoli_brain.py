
#!/usr/bin/env python3
"""Heal co-dev loop: brocc launch-grok (foreground) + brocc ask|send. pkg=ai.x.grok."""
import subprocess, sys, time, shutil
from pathlib import Path

B = Path.home() / "broccoli"
ENV = B / "meta/wire_coords.env"
LAUNCH = B / "meta/grok_launch.env"
LOG = B / "reports/agent_loop.log"
Q = B / "queue/agent_task.txt"

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {m}\n")

def load_env():
    o = {"GROK_PKG": "ai.x.grok", "GROK_ACTIVITY": "ai.x.grok.main.GrokActivity", "WIRE_MODE": "ask", "COLLAB_POLL_SEC": "0"}
    for p in (ENV, LAUNCH):
        if p.is_file():
            for line in p.read_text(errors="replace").splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    o[k.strip()] = v.strip()
    return o

def rish(cmd, t=60):
    return subprocess.run(["rish", "-c", cmd], capture_output=True, text=True, timeout=t)

def foreground_grok(cfg):
    pkg = cfg.get("GROK_PKG", "ai.x.grok")
    act = cfg.get("GROK_ACTIVITY", "ai.x.grok.main.GrokActivity")
    log(f"STEP foreground_grok pkg={pkg}")
    if shutil.which("brocc"):
        subprocess.run(["brocc", "launch-grok"], capture_output=True, text=True, timeout=90)
        time.sleep(1.2)
        log("OK foreground_brocc_launch_grok")
        return
    rish(f"am start -n {pkg}/{act}")
    time.sleep(0.8)
    log("OK foreground_rish_am_start_n")

def wire(msg, cfg):
    foreground_grok(cfg)
    if not shutil.which("brocc"):
        log("FAIL no_brocc")
        return 1
    mode = cfg.get("WIRE_MODE", "ask")
    log(f"TRY brocc_{mode} len={len(msg)}")
    if mode == "ask":
        r = subprocess.run(["brocc", "ask", msg], capture_output=True, text=True, timeout=300)
    else:
        r = subprocess.run(["brocc", "send", msg], capture_output=True, text=True, timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    log(f"brocc rc={r.returncode} tail={out[-220:].replace(chr(10), ' ')}")
    if "OK sent" in out or "BROCCOLI_DONE" in out:
        log("OK wire_brocc")
        return 0
    if r.returncode == 0 and "FAIL" not in out[-100:]:
        log("OK wire_brocc")
        return 0
    log("FAIL wire_brocc")
    return 1

def drain():
    if not Q.is_file() or Q.stat().st_size == 0:
        return
    msg = Q.read_text(encoding="utf-8", errors="replace")[:3800]
    log(f"TRY queue_bytes={len(msg)}")
    if wire(msg, load_env()) == 0:
        Q.write_text("")
        log("OK queue_cleared")

def loop():
    log("OK broccoli_brain HEAL_CODEV WIRE_MODE=" + load_env().get("WIRE_MODE", "ask"))
    while True:
        drain()
        time.sleep(float(load_env().get("COLLAB_POLL_SEC", "0") or 0))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        drain()
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "send":
        sys.exit(wire(" ".join(sys.argv[2:]), load_env()))
    loop()
