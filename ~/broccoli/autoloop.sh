#!/data/data/com.termux/files/usr/bin/bash
export BROCCOLI_ROOT="$HOME/broccoli"
LOG="$BROCCOLI_ROOT/chat_loop.log"
mkdir -p "$BROCCOLI_ROOT"/{ui,reports,meta,logs}
touch "$LOG"
echo "=== STORAGE AWARE GOD MODE $(date) ===" >> "$LOG"
while true; do
  echo "[$(date '+%H:%M:%S')] tick" >> "$LOG"
  rish -c "uiautomator dump /sdcard/broccoli_ui.xml" 2>/dev/null || true
  if [ -f "$BROCCOLI_ROOT/ui/loop_inbox.txt" ]; then
    INBOX=$(head -c 600 "$BROCCOLI_ROOT/ui/loop_inbox.txt" | tr -d '\n')
    if [ -n "$INBOX" ]; then
      python3 -c "
import subprocess, time, random, os
subprocess.run(['rish', '-c', 'input tap 540 1274'], timeout=8)
time.sleep(0.8 + random.uniform(0,0.3))
subprocess.run(['termux-clipboard-set', os.environ.get('INBOX','')], timeout=5)
subprocess.run(['rish', '-c', 'input keyevent 279'], timeout=5)
time.sleep(1.2 + random.uniform(0,0.4))
subprocess.run(['rish', '-c', 'input tap 984 1381'], timeout=8)
print('Sent')
" >> "$LOG" 2>&1 || echo "send err" >> "$LOG"
      > "$BROCCOLI_ROOT/ui/loop_inbox.txt"
    fi
  fi
  "$BROCCOLI_ROOT/sync_push.sh" >> "$LOG" 2>&1 || true
  sleep 25
done
