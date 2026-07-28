#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/broccoli"

echo "[+] Patching state_probe.py"

python3 - <<'PY'
from pathlib import Path

p = Path.home() / "broccoli/modules/state_probe.py"
s = p.read_text()

old = '''st["in_grok_chat"] = bool(st.get("on_grok") or st.get("fg_package") == "ai.x.grok")'''

new = '''st["in_grok_chat"] = bool(
        st.get("on_grok")
        or st.get("fg_package") == "ai.x.grok"
        or st.get("screen") == "grok_chat_composer"
    )'''

if old in s:
    s = s.replace(old, new)
else:
    print("state_probe already patched or pattern missing")

p.write_text(s)
PY


echo "[+] Creating Grok foreground helper"

cat > "$ROOT/modules/grok_focus.py" <<'PY'
#!/usr/bin/env python3

import subprocess
import time
import sys


def rish(cmd):
    p = subprocess.run(
        ["bash", "-c", f"printf '%s\nexit\n' '{cmd}' | rish"],
        capture_output=True,
        text=True
    )
    return p.stdout


for _ in range(25):
    out = rish(
        "dumpsys activity activities | grep mResumedActivity | head -1"
    )

    if "ai.x.grok" in out:
        print("GROK_FOREGROUND=1")
        sys.exit(0)

    time.sleep(1)

print("GROK_FOREGROUND=0")
sys.exit(1)
PY

chmod +x "$ROOT/modules/grok_focus.py"


echo "[+] Creating continuous runner"

cat > "$ROOT/grok_loop.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash

set -Eeuo pipefail

ROOT="$HOME/broccoli"

export PATH="$ROOT/bin:$PATH"

while true
do
    echo
    echo "===== BROCC GROK LOOP $(date) ====="

    echo "[1] Probe"

    brocc probe || true


    echo "[2] Harvest"

    brocc harvest || true


    echo "[3] Grok foreground check"

    python3 "$ROOT/modules/grok_focus.py" || true


    echo "[4] Sleeping"

    sleep 15

done
SH

chmod +x "$ROOT/grok_loop.sh"


echo "[+] Creating clipboard fallback test"

cat > "$ROOT/modules/clipboard_read.py" <<'PY'
#!/usr/bin/env python3

import subprocess
import shutil


def run(cmd):
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        return ""


# Preferred Termux API
if shutil.which("termux-clipboard-get"):
    data = run("termux-clipboard-get")
    if data:
        print(data)
        raise SystemExit


# Android clipboard through Shizuku/RISH
data = run(
    "printf 'cmd clipboard get\\nexit\\n' | rish"
)

if data:
    print(data)
else:
    print("NO_CLIPBOARD_ACCESS")
PY

chmod +x "$ROOT/modules/clipboard_read.py"


echo "[+] Done"
