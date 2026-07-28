#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
Q="$HOME/broccoli/queue/pending.txt"
DONE="$HOME/broccoli/queue/done.txt"
LAST="$HOME/broccoli/meta/last_task.json"
echo "=== pending ($(wc -l < "$Q" 2>/dev/null || echo 0) lines) ==="
if [ -f "$Q" ]; then
  nl -ba "$Q" 2>/dev/null || cat -n "$Q"
else
  echo "(empty — no pending.txt)"
fi
echo "=== head (next task) ==="
head -1 "$Q" 2>/dev/null || echo "(none)"
echo "=== done (tail) ==="
tail -5 "$DONE" 2>/dev/null || echo "(no done.txt)"
echo "=== last_task.json ==="
cat "$LAST" 2>/dev/null || echo "(none)"
