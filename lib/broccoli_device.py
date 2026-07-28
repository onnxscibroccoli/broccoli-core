"""
Broccoli device control — not chat-only.
Primitives: shell, tap, swipe, keyevent, start_activity, foreground_pkg, open_url.
"""
from __future__ import annotations
import json, re, subprocess
from pathlib import Path
try:
    from broccoli_rish_shell import shell, rish_ok
except ImportError:
    from broccoli.lib.broccoli_rish_shell import shell, rish_ok  # type: ignore

def device_ready() -> dict:
    return {"rish_ok": rish_ok(), "layer": "shizuku_rish"}

def tap(x: int, y: int) -> str:
    return shell(f"input tap {int(x)} {int(y)}")

def swipe(x1: int, y1: int, x2: int, y2: int, ms: int = 300) -> str:
    return shell(f"input swipe {x1} {y1} {x2} {y2} {ms}")

def keyevent(code: int) -> str:
    return shell(f"input keyevent {int(code)}")

def start_activity(component: str, extras: str = "") -> str:
    # component: com.android.chrome/com.google.android.apps.chrome.Main
    cmd = f"am start -n {component}"
    if extras:
        cmd += " " + extras
    return shell(cmd)

def open_url(url: str) -> str:
    return shell(f'am start -a android.intent.action.VIEW -d "{url}"')

def foreground_pkg() -> str:
    out = shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' | head -2")
    m = re.search(r"u0 ([\w.]+)/", out)
    return m.group(1) if m else ""

def termux_run(script: str) -> str:
    """Run shell in Termux context (local), not Shizuku."""
    p = subprocess.run(script, shell=True, text=True, capture_output=True, timeout=120)
    return (p.stdout or p.stderr or "").strip()

def grok_send_tap(ui_state_path: str | None = None) -> dict:
    """Chat send — prefer cached send from broccoli_ui state."""
    state_p = Path(ui_state_path or Path.home() / "broccoli" / "ui" / "state.json")
    sx, sy = 1001, 1338
    if state_p.is_file():
        try:
            j = json.loads(state_p.read_text())
            send = j.get("send") or j.get("grok_send")
            if isinstance(send, (list, tuple)) and len(send) >= 2:
                sx, sy = int(send[0]), int(send[1])
        except Exception:
            pass
    tap(sx, sy)
    return {"tapped": [sx, sy], "state": str(state_p)}
