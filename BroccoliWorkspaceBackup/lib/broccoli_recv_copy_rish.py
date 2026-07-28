import os, re, time
from pathlib import Path
from broccoli_rish_adb import adb_shell, launch_app_monkey

BRO = Path.home() / "broccoli"
LOG = BRO / "reports/infinite.log"

def _log(m):
    try:
        from broccoli_log import append_log
        append_log(LOG, m)
    except Exception:
        pass

def launch_grok():
    pkg = os.environ.get("BROCCOLI_GROK_PKG", "")
    _log(f"recv_copy launch_grok monkey pkg={pkg}")
    adb_shell("input keyevent KEYCODE_WAKEUP")
    time.sleep(0.2)
    rc, out = launch_app_monkey(pkg, wait_log=_log)
    time.sleep(2.0)
    rc2, focus = adb_shell("dumpsys window 2>/dev/null | grep mCurrentFocus | head -1")
    ok = pkg in (focus or "")
    _log(f"recv_copy grok_focus {'ok' if ok else 'fail'} {focus.strip()[:90]}")
    return ok

def _tap(x, y):
    adb_shell(f"input tap {int(x)} {int(y)}")

def find_copy_tap():
    remote = "/sdcard/broccoli_copy.xml"
    adb_shell(f"uiautomator dump {remote}")
    time.sleep(0.8)
    local = BRO / "state/copy_find.xml"
    local.parent.mkdir(parents=True, exist_ok=True)
    adb_shell(f"cat {remote}")
    rc, raw = adb_shell(f"cat {remote}")
    if len(raw) < 200:
        return None
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)
    copies = []
    for m in re.finditer(
        r'(?:text|content-desc)="([^"]*copy[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        raw, re.I,
    ):
        label, x1, y1, x2, y2 = m.groups()
        copies.append((int(x1), int(y1), int(x2), int(y2), label))
    if not copies:
        return None
    x1, y1, x2, y2, label = max(copies, key=lambda c: c[3])
    _log(f"recv_copy found {label[:40]}")
    return (x1 + x2) // 2, (y1 + y2) // 2

def recv_via_copy_rish(task=""):
    _log("recv_copy_rish start")
    if not launch_grok():
        return "", {"source": "copy_rish", "error": "grok_not_focused"}
    lp = os.environ.get("BROCCOLI_LONGPRESS", "540,1200")
    x, y = [int(v) for v in lp.split(",")]
    adb_shell(f"input swipe 540 2000 540 450 350")
    time.sleep(0.5)
    adb_shell(f"input swipe {x} {y} {x} {y} 900")
    time.sleep(1.0)
    tap = find_copy_tap()
    if not tap:
        _log("recv_copy_rish no_copy_button")
        return "", {"source": "copy_rish", "error": "no_copy"}
    _tap(*tap)
    _log(f"recv_copy_rish tap_copy {tap[0]} {tap[1]}")
    time.sleep(0.5)
    import subprocess
    r = subprocess.run("termux-clipboard-get", shell=True, capture_output=True, text=True, timeout=10)
    clip = (r.stdout or "").strip()
    if task and "LOOP_OK" in task.upper() and "LOOP_OK" not in clip.upper():
        return "", {"source": "copy_rish", "error": "no_loop_ok", "clip_head": clip[:80]}
    if clip:
        _log(f"recv_copy_rish ok len={len(clip)}")
        (BRO / "inbox/grok_reply.txt").write_text(clip, encoding="utf-8")
        return clip, {"source": "copy_rish"}
    return "", {"source": "copy_rish", "error": "empty_clip"}
