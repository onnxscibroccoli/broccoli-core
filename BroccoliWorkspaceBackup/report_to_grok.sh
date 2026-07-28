#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
bash "$B/ui_pull.sh" 2>/dev/null || true
python3 "$B/screen_state.py" >"$B/screen_state.json" 2>/dev/null || true
{
  echo "BROCCOLI_PING"
  echo "time=$(date -Iseconds)"
  cat "$B/screen_state.json"
  echo "REPLY: CMD:cd $B && brocc cycle"
} > "$B/outbox_context.txt"
bash "$B/chat_inject.sh"
echo "inject_exit=$?"
