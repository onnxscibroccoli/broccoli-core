#!/data/data/com.termux/files/usr/bin/bash
export BROCCOLI_ROOT="$HOME/broccoli"
export PYTHONPATH="$BROCCOLI_ROOT:$PYTHONPATH"
LOG="$BROCCOLI_ROOT/chat_loop.log"
mkdir -p "$BROCCOLI_ROOT"/{ui,reports,meta,logs,data/harvest,research}
touch "$LOG"

echo "=== Broccoli PRODUCTION + Dynamic Send $(date -Iseconds) ===" >> "$LOG"

while true; do
    echo "[$(date '+%H:%M:%S')] tick" >> "$LOG"

    rish -c "uiautomator dump /sdcard/broccoli_ui.xml" 2>/dev/null || true
    rish -c "cat /sdcard/broccoli_ui.xml" > "$BROCCOLI_ROOT/ui/last_ui.xml" 2>/dev/null || true
    cp -f "$BROCCOLI_ROOT/ui/last_ui.xml" "$BROCCOLI_ROOT/ui/latest.xml" 2>/dev/null || true

    python3 - <<'PY' >> "$LOG" 2>&1 || echo "harvest err" >> "$LOG"
import sys, os
sys.path.insert(0, os.path.expanduser("\~/broccoli"))
from lib.foreground_detect import detect_foreground
from modules.chat_store import harvest_payload
fg = detect_foreground()
print("FG:", getattr(fg, 'package', 'none'), "conf:", getattr(fg, 'confidence', 0))
h = harvest_payload("\~/broccoli")
print("Harvest:", h)
PY

    python3 - <<'PY' >> "$LOG" 2>&1 || echo "governor err" >> "$LOG"
import sys, os
sys.path.insert(0, os.path.expanduser("\~/broccoli"))
from lib.auto_governor import decide
d = decide()
print("Governor:", d.reason, "sleep", d.sleep_sec, "task", d.task.get("id"))
PY

    if [ -f "$BROCCOLI_ROOT/ui/loop_inbox.txt" ]; then
        INBOX=$(head -c 800 "$BROCCOLI_ROOT/ui/loop_inbox.txt" | tr -d '\n')
        if [ -n "$INBOX" ]; then
            echo "Sending: ${INBOX:0:60}..." >> "$LOG"
            python3 - <<'SEND' >> "$LOG" 2>&1 || echo "send err" >> "$LOG"
import subprocess, time, os
subprocess.run(["rish", "-c", "input tap 540 1274"], timeout=8)  # composer
time.sleep(0.7)
subprocess.run(["termux-clipboard-set", os.environ.get("INBOX", "")], timeout=5)
subprocess.run(["rish", "-c", "input keyevent 279"], timeout=5)  # paste
time.sleep(1.0)  # longer wait for keyboard
subprocess.run(["rish", "-c", "input tap 984 1381"], timeout=8)  # send
print("Sent OK")
SEND
            > "$BROCCOLI_ROOT/ui/loop_inbox.txt"
        fi
    fi

    "$BROCCOLI_ROOT/sync_push.sh" >> "$LOG" 2>&1 || true
    sleep 25
done
