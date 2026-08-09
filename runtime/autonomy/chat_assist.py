"""Chat assist: open AI app, detect foreground, optional armed auto-reply."""
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
    for wrapper in (["rish", "-c", cmd], ["sh", "-c", cmd]):
        code, out = _run(wrapper, timeout=timeout)
        if code == 0 and out.strip():
            return code, out
        if code == 0:
            return code, out
    return 1, ""


def detect_foreground() -> Tuple[Optional[str], str]:
    text = ""
    for c in ("dumpsys activity activities", "dumpsys window windows", "dumpsys activity top"):
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
    attempts = []
    for cmd in (
        f"monkey -p {package} -c android.intent.category.LAUNCHER 1",
        f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {package}",
        f"am start -n {package}/.MainActivity",
    ):
        code, out = _rish(cmd)
        attempts.append({"cmd": cmd, "code": code, "out": out[:200]})
        if code == 0:
            for wait in (1.5, 2.5, 3.5):
                time.sleep(wait)
                fg, src = detect_foreground()
                if fg == package or (fg and fg.startswith(package)):
                    return {
                        "ok": True,
                        "package": package,
                        "foreground": fg,
                        "foreground_source": src,
                        "attempts": attempts,
                        "waited": wait,
                    }
            # last sample after retries
            fg, src = detect_foreground()
            if fg == package or (fg and fg.startswith(package)):
                return {
                    "ok": True,
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
    result: Dict[str, Any] = {"text_len": len(text), "clipboard": False, "send": "skipped"}
    result["clipboard"] = _set_clipboard(text)
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

    ui_snapshot = None
    try:
        from runtime.autonomy.aim_ui_dump import dump_and_parse
        ui_snapshot = dump_and_parse()
    except Exception as e:
        ui_snapshot = {"ok": False, "error": str(e)}

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
                if not (fg == package or (fg and package in (fg or ""))):
                    opened = open_chat(package)
                    fg = opened.get("foreground")
                try:
                    from runtime.autonomy.aim_ui_dump import dump_and_parse, tap
                    ud = dump_and_parse()
                    pr = (ud or {}).get("parse") or {}
                except Exception:
                    ud, pr = None, {}
                send_result = send_text_best_effort(text, package=package)
                send_result["ui"] = {
                    "has_composer": pr.get("has_composer"),
                    "send": pr.get("send"),
                    "mic": pr.get("mic"),
                }
                if send_result.get("clipboard") and isinstance(pr.get("send"), dict):
                    s = pr["send"]
                    if "x" in s and "y" in s:
                        try:
                            comp = pr.get("composer") or {}
                            if "x" in comp and "y" in comp:
                                tap(int(comp["x"]), int(comp["y"]))
                                time.sleep(0.3)
                                _set_clipboard(text)
                                _rish("input keyevent 279")
                                time.sleep(0.2)
                            send_result["tap_send"] = tap(int(s["x"]), int(s["y"]))
                        except Exception as e:
                            send_result["tap_send"] = {"ok": False, "error": str(e)}
                done = meta / "outbox_sent"
                done.mkdir(parents=True, exist_ok=True)
                msg_path.rename(done / f"{int(time.time())}_{msg_path.name}")

    mode = "assisting" if ai_in_use else "active"
    parse = (ui_snapshot or {}).get("parse") if isinstance(ui_snapshot, dict) else None
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
        "ui": {
            "has_composer": (parse or {}).get("has_composer") if isinstance(parse, dict) else None,
            "composer": (parse or {}).get("composer") if isinstance(parse, dict) else None,
            "send": (parse or {}).get("send") if isinstance(parse, dict) else None,
            "mic": (parse or {}).get("mic") if isinstance(parse, dict) else None,
        },
    }
    (meta / "chat_assist.json").write_text(json.dumps(payload, indent=2))
    assist_path = meta / "assist.json"
    try:
        base = json.loads(assist_path.read_text()) if assist_path.is_file() else {}
    except Exception:
        base = {}
    base.update(
        {
            "timestamp": payload["timestamp"],
            "assist_mode": mode,
            "foreground_package": fg,
            "foreground_source": src,
            "ai_tool_in_use": ai_in_use,
            "chat_assist": payload.get("ui"),
        }
    )
    assist_path.write_text(json.dumps(base, indent=2))
    return payload


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Broccoli chat assist once")
    p.add_argument("--app", default="grok")
    p.add_argument("--open", action="store_true")
    p.add_argument("--auto-reply", action="store_true")
    args = p.parse_args()
    print(json.dumps(run_once(app_key=args.app, open_if_needed=args.open, auto_reply=args.auto_reply), indent=2))


if __name__ == "__main__":
    main()
