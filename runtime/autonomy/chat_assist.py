"""Chat assist: open AI app, detect foreground, optional armed auto-reply.

Auto-send is gated:
  - meta/always_on/auto_reply.enabled must exist
  - meta/always_on/outbox/*.txt messages (consumed after send attempt)
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

AI_PACKAGES = {
    "grok": "ai.x.grok",
    "chatgpt": "com.openai.chatgpt",
    "claude": "com.anthropic.claude",
    "bard": "com.google.android.apps.bard",
    "gemini": "com.google.android.apps.bard",
    "copilot": "com.microsoft.copilot",
}


def _run(cmd: List[str], timeout: int = 12) -> Tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, str(e)


def _rish(cmd: str, timeout: int = 12) -> Tuple[int, str]:
    # Prefer rish if present
    for wrapper in (
        ["rish", "-c", cmd],
        ["sh", "-c", cmd],
    ):
        code, out = _run(wrapper, timeout=timeout)
        if code == 0 and out.strip():
            return code, out
        if code == 0:
            return code, out
    return 1, ""


def detect_foreground() -> Tuple[Optional[str], str]:
    cmds = [
        "dumpsys activity activities",
        "dumpsys window windows",
        "dumpsys activity top",
    ]
    text = ""
    for c in cmds:
        code, out = _rish(c)
        if out.strip():
            text = out
            break
    if not text:
        return None, "unavailable"
    patterns = [
        r"topResumedActivity.*?\s+([a-zA-Z0-9_.]+)/",
        r"mResumedActivity.*?\s+([a-zA-Z0-9_.]+)/",
        r"mFocusedApp.*?\s+([a-zA-Z0-9_.]+)/",
        r"ActivityRecord\{[^ ]+\s+[^ ]+\s+([a-zA-Z0-9_.]+)/",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1), "detected"
    return None, "unknown"


def open_chat(package: str = "ai.x.grok") -> Dict[str, Any]:
    """Bring package to foreground via am/monkey (best effort)."""
    attempts = []
    for cmd in (
        f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {package}",
        f"monkey -p {package} -c android.intent.category.LAUNCHER 1",
        f"am start -n {package}/.MainActivity",
    ):
        code, out = _rish(cmd)
        attempts.append({"cmd": cmd, "code": code, "out": out[:200]})
        if code == 0:
            time.sleep(1.2)
            fg, src = detect_foreground()
            return {
                "ok": bool(fg == package or (fg and fg.startswith(package))),
                "package": package,
                "foreground": fg,
                "foreground_source": src,
                "attempts": attempts,
            }
    fg, src = detect_foreground()
    return {
        "ok": bool(fg == package or (fg and package in (fg or ""))),
        "package": package,
        "foreground": fg,
        "foreground_source": src,
        "attempts": attempts,
    }


def _set_clipboard(text: str) -> bool:
    code, _ = _run(["termux-clipboard-set", text], timeout=8)
    return code == 0


def send_text_best_effort(text: str, package: str = "ai.x.grok") -> Dict[str, Any]:
    """Paste via clipboard + optional existing send helpers. Does not invent UI taps blindly."""
    result: Dict[str, Any] = {"text_len": len(text), "clipboard": False, "send": "skipped"}
    result["clipboard"] = _set_clipboard(text)
    # Prefer project send helpers if present
    root = Path.home() / "broccoli-core"
    for helper in (
        root / "tools" / "a11y_send_round.sh",
        root / "tools" / "wire_send_fast.sh",
        root / "tools" / "send_now.sh",
    ):
        if helper.is_file():
            code, out = _run(["bash", str(helper), text], timeout=45)
            result["send"] = helper.name
            result["send_code"] = code
            result["send_out"] = out[-500:]
            result["ok"] = code == 0
            return result
    result["ok"] = result["clipboard"]
    result["note"] = "clipboard only; no send helper succeeded"
    return result


def run_once(
    app_key: str = "grok",
    open_if_needed: bool = True,
    auto_reply: bool = False,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    root = Path(root or (Path.home() / "broccoli-core"))
    meta = root / "meta" / "always_on"
    meta.mkdir(parents=True, exist_ok=True)
    package = AI_PACKAGES.get(app_key, app_key if "." in app_key else "ai.x.grok")

    fg, src = detect_foreground()
    ai_keys = set(AI_PACKAGES.values())
    ai_in_use = bool(fg and any(fg == p or fg.startswith(p + ".") for p in ai_keys))

    opened = None
    if open_if_needed and not (fg == package or (fg and fg.startswith(package))):
        opened = open_chat(package)
        fg, src = opened.get("foreground"), opened.get("foreground_source", src)
        ai_in_use = bool(fg and any(fg == p or fg.startswith(p + ".") for p in ai_keys))

    send_result = None
    armed = (meta / "auto_reply.enabled").is_file()
    outbox = meta / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    if auto_reply and armed:
        msgs = sorted(outbox.glob("*.txt"), key=lambda p: p.stat().st_mtime)
        if msgs:
            msg_path = msgs[0]
            text = msg_path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                if not (fg == package or (fg and package in fg)):
                    opened = open_chat(package)
                    fg = opened.get("foreground")
                send_result = send_text_best_effort(text, package=package)
                # consume message regardless of send outcome to avoid loops
                done = meta / "outbox_sent"
                done.mkdir(parents=True, exist_ok=True)
                msg_path.rename(done / f"{int(time.time())}_{msg_path.name}")

    mode = "degraded"
    if ai_in_use:
        mode = "assisting"
    elif src != "unavailable":
        mode = "active"
    else:
        mode = "active"  # still assist-ready without dumpsys

    payload = {
        "timestamp": int(time.time()),
        "assist_mode": mode,
        "package": package,
        "foreground_package": fg,
        "foreground_source": src,
        "ai_tool_in_use": ai_in_use,
        "opened": opened,
        "auto_reply_armed": armed,
        "send": send_result,
    }
    (meta / "chat_assist.json").write_text(json.dumps(payload, indent=2))
    # merge into assist.json for always_on consumers
    assist_path = meta / "assist.json"
    try:
        base = json.loads(assist_path.read_text()) if assist_path.is_file() else {}
    except Exception:
        base = {}
    base.update(
        {
            "timestamp": payload["timestamp"],
            "assist_mode": mode if mode == "assisting" else base.get("assist_mode", mode),
            "foreground_package": fg,
            "foreground_source": src,
            "ai_tool_in_use": ai_in_use,
            "chat_assist": {
                "package": package,
                "auto_reply_armed": armed,
                "send": send_result,
            },
        }
    )
    assist_path.write_text(json.dumps(base, indent=2))
    return payload


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Broccoli chat assist once")
    p.add_argument("--app", default="grok", help="grok|chatgpt|claude|bard|copilot|package.name")
    p.add_argument("--open", action="store_true", help="Open app if not foreground")
    p.add_argument("--auto-reply", action="store_true", help="Send next outbox msg if armed")
    args = p.parse_args()
    result = run_once(app_key=args.app, open_if_needed=args.open, auto_reply=args.auto_reply)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
