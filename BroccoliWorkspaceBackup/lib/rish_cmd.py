import os, random, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "lib", "rish_cmd.sh")
def run(cmd, timeout=15):
    return subprocess.run(["bash", SH, cmd], capture_output=True, text=True, timeout=timeout, cwd=ROOT)
def tap(x, y, jitter=0):
    if jitter:
        x += random.randint(-jitter, jitter)
        y += random.randint(-jitter, jitter)
    return run(f"input tap {int(x)} {int(y)}", 10).returncode == 0
def tap_long(x, y, ms=90, jitter=0):
    if jitter:
        x += random.randint(-jitter, jitter)
        y += random.randint(-jitter, jitter)
    x, y = int(x), int(y)
    return run(f"input swipe {x} {y} {x} {y} {int(ms)}", 12).returncode == 0
def keyevent(c):
    return run(f"input keyevent {int(c)}", 10).returncode == 0
