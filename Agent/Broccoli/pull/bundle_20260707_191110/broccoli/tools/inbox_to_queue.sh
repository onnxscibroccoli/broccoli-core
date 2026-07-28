#!/data/data/com.termux/files/usr/bin/bash
set -eu
Q="$HOME/broccoli/queue/pending.txt"
TASK="$HOME/broccoli/task_box.txt"
[ -f "$TASK" ] || exit 0
LINE="$(grep -v '^#' "$TASK" | sed '/^[[:space:]]*$/d' | head -1)"
[ -n "$LINE" ] || exit 0
case "$LINE" in ASK|*) ASK="$LINE" ;; *) ASK="ASK|$LINE" ;; esac
printf '%s\n' "$ASK" > "$Q"
echo "queue=$ASK"
