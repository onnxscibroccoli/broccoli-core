import os, subprocess
from pathlib import Path
from broccoli_adb_ui import full_round_adb, normalize_task
PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
def clip_set(text):
    text = normalize_task(text)
    cs = Path(PREFIX) / "bin/termux-clipboard-set"
    if not cs.is_file(): return False
    subprocess.run([str(cs), text], timeout=8, check=False)
    return True
def full_round(task):
    return full_round_adb(task, clip_set)
