#!/usr/bin/env python3
"""Dump source health — does not use settings (broken on many Termux)."""
import os, re, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = "/sdcard/broccoli_window_dump.xml"

def run(ctx=None):
    from modules.registry import ModuleResult
    reasons = []
    data = {}

    # settings often fails on Termux
    r = subprocess.run(["settings", "get", "secure", "enabled_accessibility_services"],
                       capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        data["enabled_services"] = (r.stdout or "").strip()
    else:
        data["enabled_services"] = None
        reasons.append("settings_unavailable")

    ds = subprocess.run(["dumpsys", "accessibility"], capture_output=True, text=True, timeout=8)
    if ds.stdout:
        m = re.search(r"mEnabledServices=([^\n]+)", ds.stdout)
        if m:
            data["dumpsys_enabled"] = m.group(1).strip()
        data["dumpsys_head_ok"] = True
    else:
        reasons.append("dumpsys_empty")

    if os.path.isfile(DUMP):
        data["dump_bytes"] = os.path.getsize(DUMP)
        data["dump_age_s"] = time.time() - os.path.getmtime(DUMP)
        try:
            xml = open(DUMP, encoding="utf-8", errors="ignore").read(50000)
            pkgs = re.findall(r'package="([^"]+)"', xml)
            data["dump_top_package"] = max(set(pkgs), key=pkgs.count) if pkgs else None
        except Exception:
            data["dump_top_package"] = None
    else:
        data["dump_bytes"] = 0
        reasons.append("no_dump_file")

    fg = subprocess.run(["python3", "screen_state.py"], cwd=ROOT, capture_output=True, text=True, timeout=12)
    try:
        import json
        st = json.loads(fg.stdout or "{}")
        data["fg_package"] = st.get("fg_package")
    except Exception:
        data["fg_package"] = None

    ok = (
        (data.get("dump_bytes") or 0) > 8000
        and data.get("dump_top_package") == "ai.x.grok"
        and data.get("fg_package") == "ai.x.grok"
    )
    if data.get("dump_age_s", 999) > 120:
        reasons.append("dump_stale")
    return ModuleResult(ok, "a11y_probe", reason=";".join(reasons) or "ok", data=data)

def precondition(state: dict) -> tuple[bool, str]:
    return True, "ok"
