"""Where is automation running? Primary vs secondary / virtual display."""
import re, subprocess

def _run(cmd, t=12):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception:
        return type("R", (), {"stdout": ""})()

def grok_focus_line():
    r = _run("dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -4")
    return (r.stdout or "").strip()

def display_summary():
    r = _run("dumpsys display 2>/dev/null | head -80")
    r2 = _run("dumpsys activity activities 2>/dev/null | grep -E 'Display|mResumedActivity' | head -15")
    return {
        "focus": grok_focus_line(),
        "display_head": (r.stdout or "")[:1200],
        "activity_head": (r2.stdout or "")[:800],
        "grok_in_focus": "grok" in grok_focus_line().lower(),
    }

def log_display(rep_path):
    import json
    from pathlib import Path
    s = display_summary()
    Path(rep_path).write_text(json.dumps(s, indent=2))
    print("DISPLAY", "grok_focus=", s["grok_in_focus"], flush=True)
    print(s["focus"], flush=True)
    return s
