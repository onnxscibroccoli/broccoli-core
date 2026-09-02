"""Termux / Android privilege ladder.

Try rish (Shizuku) first, then raw svc/cmd. Never claim success on a
non-zero exit. Phone-first, CI-safe (missing binaries = simulated).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _which(name: str) -> Optional[str]:
    p = shutil.which(name)
    if p:
        return p
    prefix = os.environ.get("PREFIX", "")
    for cand in (
        os.environ.get("RISH_BIN") if name == "rish" else None,
        f"{prefix}/bin/{name}" if prefix else None,
        str(Path.home() / "rish" / name),
        str(Path.home() / "broccoli-core" / f"{name}.sh"),
        str(Path.home() / "broccoli-core" / name),
    ):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def run(argv: Sequence[str], timeout: float = 12) -> Dict[str, Any]:
    try:
        r = subprocess.run(
            list(argv), capture_output=True, text=True, timeout=timeout
        )
        return {
            "argv": list(argv),
            "returncode": r.returncode,
            "stdout": (r.stdout or "").strip()[:400],
            "stderr": (r.stderr or "").strip()[:400],
            "ok": r.returncode == 0,
        }
    except FileNotFoundError:
        return {
            "argv": list(argv),
            "returncode": 127,
            "stdout": "",
            "stderr": "not found",
            "ok": False,
            "simulated": True,
        }
    except Exception as exc:
        return {
            "argv": list(argv),
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "ok": False,
        }


def privileged(shell: str, timeout: float = 12) -> Dict[str, Any]:
    """Run a shell string with the highest privilege we actually have."""
    rish = _which("rish")
    if rish:
        out = run([rish, "-c", shell], timeout=timeout)
        out["via"] = "rish"
        return out
    wrapper = _which("rish.sh") or str(Path.home() / "broccoli-core" / "rish.sh")
    if os.path.isfile(wrapper):
        out = run(["bash", wrapper, "-c", shell], timeout=timeout)
        out["via"] = "rish.sh"
        return out
    out = run(["sh", "-c", shell], timeout=timeout)
    out["via"] = "sh"
    return out


def bluetooth_state() -> Dict[str, Any]:
    probes = [
        "settings get global bluetooth_on",
        "cmd bluetooth_manager get-state",
        "dumpsys bluetooth_manager | grep -m1 state",
    ]
    for cmd in probes:
        r = privileged(cmd)
        text = (r.get("stdout") or "") + " " + (r.get("stderr") or "")
        low = text.lower()
        if r.get("ok") or text.strip():
            on = None
            if "1" == text.strip() or "state: on" in low or "state_on" in low:
                on = True
            elif "0" == text.strip() or "state: off" in low or "state_off" in low:
                on = False
            r["on"] = on
            r["probe"] = cmd
            return r
    return {"ok": False, "on": None, "note": "no privileged probe"}


def bluetooth_set(want_on: Optional[bool] = None, toggle: bool = False) -> Dict[str, Any]:
    if toggle:
        st = bluetooth_state()
        want_on = not bool(st.get("on"))
    verb = "enable" if want_on else "disable"
    attempts: List[Dict[str, Any]] = []
    for cmd in (
        f"svc bluetooth {verb}",
        f"cmd bluetooth {verb}",
        f"cmd bluetooth_manager {verb}",
        f"settings put global bluetooth_on {1 if want_on else 0}",
    ):
        r = privileged(cmd)
        r["wanted"] = verb
        attempts.append(r)
        if r.get("ok"):
            after = bluetooth_state()
            return {
                "ok": True,
                "action": "bluetooth",
                "state": "on" if want_on else "off",
                "via": r.get("via"),
                "cmd": cmd,
                "returncode": r.get("returncode"),
                "stdout": r.get("stdout"),
                "stderr": r.get("stderr"),
                "after": after.get("on"),
            }
    last = attempts[-1] if attempts else {}
    return {
        "ok": False,
        "action": "bluetooth",
        "state": "unchanged",
        "wanted": verb,
        "returncode": last.get("returncode"),
        "stdout": last.get("stdout"),
        "stderr": last.get("stderr") or "no privileged bluetooth control",
        "attempts": [{"cmd": a.get("wanted"), "rc": a.get("returncode"), "via": a.get("via")} for a in attempts],
        "note": "need Shizuku/rish or shell for svc bluetooth",
    }


def notify(text: str, title: str = "Broccoli") -> Dict[str, Any]:
    tn = _which("termux-notification")
    if tn:
        r = run([tn, "-t", title, "-c", text])
        r["action"] = "notification"
        return r
    toast = _which("termux-toast")
    if toast:
        r = run([toast, text])
        r["action"] = "notification"
        r["via"] = "toast"
        return r
    return {
        "ok": True,
        "action": "notification",
        "simulated": True,
        "text": text,
        "note": "termux-api not installed; notification printed only",
    }
