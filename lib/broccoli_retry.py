"""4 retries, 1s delay between tries. Per-step, not whole pipeline."""
from __future__ import annotations
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
RETRIES = int(os.environ.get("BROCC_RETRIES", "4"))
DELAY_SEC = float(os.environ.get("BROCC_RETRY_DELAY", "1"))


class StepFail(Exception):
    def __init__(self, code: str, hint: str = "", fatal: bool = False):
        self.code = code
        self.hint = hint
        self.fatal = fatal
        super().__init__(code)


def run_step(name: str, fn: Callable[[], bool], hint_on_fail: str = "") -> None:
    last_err = ""
    for attempt in range(1, RETRIES + 1):
        try:
            if fn():
                print(f"[retry] {name} OK try={attempt}")
                return
            last_err = "returned False"
        except StepFail as e:
            if e.fatal:
                print(f"[retry] {name} FATAL {e.code} {e.hint}")
                raise
            last_err = e.code
            print(f"[retry] {name} try={attempt}/{RETRIES} {e.code}")
        except Exception as e:
            last_err = str(e)
            print(f"[retry] {name} try={attempt}/{RETRIES} err={e}")
        if attempt < RETRIES:
            time.sleep(DELAY_SEC)
    raise StepFail(f"{name}_FAILED", hint_on_fail or last_err, fatal=False)


def snap() -> Path:
    dump = ROOT / "window_dump.xml"
    subprocess.run(["bash", str(ROOT / "ui_snapshot.sh")], cwd=ROOT, capture_output=True, timeout=15)
    if not dump.is_file() or dump.stat().st_size < 200:
        raise StepFail("NO_DUMP", "Run ui_snapshot / enable a11y", fatal=True)
    return dump


def dump_text() -> str:
    return snap().read_text(encoding="utf-8", errors="ignore")


def grok_foreground(xml: str) -> bool:
    return any(x in xml.lower() for x in ("grok", "x.ai", "xai", "com.twitter"))


def has_input(xml: str) -> bool:
    return "edittext" in xml.lower() or "compose" in xml.lower() or "input" in xml.lower()


def has_send(xml: str) -> bool:
    return "send" in xml.lower() or "submit" in xml.lower()


def tap_profile(key: str) -> bool:
    prof = ROOT / "chat_profile.json"
    if not prof.is_file():
        return False
    j = json.loads(prof.read_text(encoding="utf-8"))
    p = j.get(key) or j.get(f"{key}_button")
    if not p:
        return False
    x, y = int(p["x"]), int(p["y"])
    subprocess.run(["input", "tap", str(x), str(y)], capture_output=True, timeout=5)
    return True


def tap_send_from_dump(xml: str) -> bool:
    import re
    for line in xml.splitlines():
        if "send" not in line.lower():
            continue
        m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', line)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            subprocess.run(
                ["input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2)],
                capture_output=True,
                timeout=5,
            )
            return True
    return tap_profile("send")


def set_clipboard(msg: str) -> None:
    subprocess.run(["termux-clipboard-set"], input=msg.encode(), capture_output=True, timeout=5)


def launch_grok() -> None:
    brocc = ROOT / "bin" / "brocc"
    if brocc.is_file():
        r = subprocess.run(
            ["bash", str(brocc), "launch-grok"],
            cwd=ROOT,
            capture_output=True,
            timeout=25,
            text=True,
        )
        if r.returncode == 0:
            return
    for script in ("grok_launch.sh", "go_to_grok_chat.sh"):
        sp = ROOT / script
        if sp.is_file():
            subprocess.run(
                ["timeout", "15", "bash", str(sp)],
                cwd=ROOT,
                capture_output=True,
                timeout=20,
            )
            return
    raise StepFail("NO_LAUNCHER", "Run: brocc launch-grok", fatal=True)
