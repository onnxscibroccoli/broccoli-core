#!/data/data/com.termux/files/usr/bin/bash
PREV="$HOME/broccoli/meta/last_idle_sec"
NOW="$(bash "$HOME/broccoli/lib/user_idle_sec.sh" 2>/dev/null || echo 99)"
echo "$NOW" > "$PREV.new"
if [ -f "$PREV" ]; then
  P=$(cat "$PREV")
  if [ "$P" -ge 3 ] && [ "$NOW" -lt 2 ]; then
    echo "$(date -Iseconds) user_touch_detected idle ${P}->${NOW}" >> "$HOME/broccoli/reports/manual_gap.jsonl"
    bash "$HOME/broccoli/lib/input_snapshot.sh" >/dev/null 2>&1 || true
  fi
fi
mv -f "$PREV.new" "$PREV" 2>/dev/null || echo "$NOW" > "$PREV"
