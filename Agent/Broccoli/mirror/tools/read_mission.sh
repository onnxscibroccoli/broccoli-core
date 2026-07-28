#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
INS=""
for f in "$HOME/broccoli/INSTRUCTIONS.md" "$HOME/broccoli/instructions.md" "$HOME/broccoli/README.md"; do
  [ -f "$f" ] && INS="$f" && break
done
TASK=""
for f in "$HOME/broccoli/task_box.txt" "$HOME/broccoli/inbox/task.txt" "$HOME/broccoli/TASK.md" "$HOME/broccoli/tasks/current.md"; do
  [ -f "$f" ] && TASK="$f" && break
done
Q="$HOME/broccoli/queue/pending.txt"
echo "INSTRUCTIONS=${INS:-none}"
echo "TASK_BOX=${TASK:-none}"
echo "QUEUE=$Q"
[ -n "$INS" ] && echo "=== INSTRUCTIONS (head) ===" && sed -n '1,60p' "$INS"
[ -n "$TASK" ] && echo "=== TASK BOX ===" && cat "$TASK"
[ -f "$Q" ] && echo "=== QUEUE ===" && cat "$Q"
