#!/usr/bin/env python3
"""Run adb shell via rish (Shizuku). Falls back to adb if rish missing."""
import shutil, subprocess, sys

def have(cmd):
    return shutil.which(cmd) is not None

def rish_shell(cmd, t=30):
    """cmd = raw shell string for device (am start, dumpsys, ...)"""
    if have("rish"):
        full = ["rish", "-c", cmd]
    elif have("adb"):
        full = ["adb", "shell", cmd]
    else:
        return type("R", (), {"stdout": "", "stderr": "no rish/adb", "returncode": 127})()
    try:
        return subprocess.run(full, capture_output=True, text=True, timeout=t)
    except Exception as e:
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

def grok_focused():
    r = rish_shell("dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp' | head -2")
    return "grok" in (r.stdout or "").lower()

def resolve_grok_activity():
    for comp in (
        "ai.x.grok/.MainActivity",
        "ai.x.grok/.ui.main.MainActivity",
        "ai.x.grok/com.xai.grok.MainActivity",
    ):
        r = rish_shell(f"cmd package resolve-activity --brief {comp} 2>/dev/null | tail -1")
        if r.stdout and "grok" in r.stdout.lower() and "No activity" not in r.stdout:
            line = r.stdout.strip().split()[-1]
            if "/" in line:
                return line
    return "ai.x.grok/.MainActivity"

def open_grok_activity():
    pkg = "ai.x.grok"
    comp = resolve_grok_activity()
    cmds = [
        f"am start -W -n {comp}",
        f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1",
        f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {pkg}",
    ]
    last = ""
    for c in cmds:
        r = rish_shell(c, t=25)
        last = (r.stdout or "") + (r.stderr or "")
        if grok_focused():
            return True, c, last
    return grok_focused(), cmds[0], last

if __name__ == "__main__":
    ok, used, out = open_grok_activity()
    print("OK" if ok else "FAIL", used)
    print(out[:500])
    sys.exit(0 if ok else 1)
