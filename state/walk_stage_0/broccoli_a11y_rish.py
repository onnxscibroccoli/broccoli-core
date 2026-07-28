"""
Accessibility-first automation via Rish + Broccoli A11y helper APK.
Falls back to node-bounds click only if helper not installed.
"""
import os, re, time, json, subprocess
from pathlib import Path
from broccoli_rish_shell import shell, rish_path

BRO = Path.home() / "broccoli"
A11Y_PKG = os.environ.get("BROCCOLI_A11Y_PKG", "ai.broccoli.a11y")
A11Y_ACTION = "com.broccoli.a11y.ACTION"
GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")

def _am_broadcast(extra_args):
    cmd = f'am broadcast -a {A11Y_ACTION} -p {A11Y_PKG} ' + " ".join(extra_args)
    rc, out = shell(cmd, timeout=12)
    return rc, out

def a11y_installed():
    rc, out = shell(f"pm path {A11Y_PKG}")
    return rc == 0 and "package:" in out

def a11y_service_enabled():
    rc, out = shell("settings get secure enabled_accessibility_services")
    return A11Y_PKG in (out or "")

def a11y_click_text(text, pkg=None):
    pkg = pkg or GROK
    rc, out = _am_broadcast([
        '--es op click_text',
        f'--es target_pkg {pkg}',
        f'--es text "{text}"',
    ])
    time.sleep(0.35)
    return rc == 0, out

def a11y_click_rid(resource_id, pkg=None):
    pkg = pkg or GROK
    rc, out = _am_broadcast([
        '--es op click_rid',
        f'--es target_pkg {pkg}',
        f'--es rid "{resource_id}"',
    ])
    time.sleep(0.35)
    return rc == 0, out

def a11y_set_text(text, pkg=None):
    pkg = pkg or GROK
    # escape for shell: use file + content provider pattern via broadcast chunks
    safe = text.replace('"', "'")[:4000]
    rc, out = _am_broadcast([
        '--es op set_text_focused',
        f'--es target_pkg {pkg}',
        f'--es text "{safe}"',
    ])
    time.sleep(0.25)
    return rc == 0, out

def a11y_click_send(pkg=None):
    pkg = pkg or GROK
    for op in (
        ['--es op click_send', f'--es target_pkg {pkg}'],
        ['--es op click_text', f'--es target_pkg {pkg}', '--es text Send'],
        ['--es op click_desc', f'--es target_pkg {pkg}', '--es text send'],
    ):
        rc, out = _am_broadcast(op)
        time.sleep(0.35)
        if "OK" in out or rc == 0:
            return True, out
    return False, out

def a11y_status():
    return {
        "installed": a11y_installed(),
        "enabled": a11y_service_enabled(),
        "rish": bool(rish_path()),
        "pkg": A11Y_PKG,
    }

def open_accessibility_settings():
    shell("am start -a android.settings.ACCESSIBILITY_SETTINGS")
