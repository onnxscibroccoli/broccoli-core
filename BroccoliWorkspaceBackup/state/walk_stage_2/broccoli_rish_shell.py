import os, re, subprocess, shutil
from pathlib import Path

def rish_path():
    for c in (os.environ.get("BROCCOLI_RISH"), Path(os.environ["PREFIX"])/"bin/rish", Path.home()/"rish"):
        if c and Path(str(c)).is_file():
            return str(c)
    return shutil.which("rish")

def shell(cmd, timeout=45):
    env = os.environ.copy()
    env.setdefault("RISH_APPLICATION_ID", "com.termux")
    rish = rish_path()
    if rish:
        p = subprocess.run([rish, "-c", cmd], capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    adb = shutil.which("adb")
    if adb:
        p = subprocess.run([adb, "shell", cmd], capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    p = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def rish_ok():
    rc, out = shell("whoami; id")
    return rc == 0 and ("shell" in out or "uid=" in out), out.strip()[:400]

def wm_size():
    rc, out = shell("wm size")
    m = re.search(r"(\d+)x(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)
