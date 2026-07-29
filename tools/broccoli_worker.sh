#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
Q="$B/queue/pending.txt"
[ -s "$Q" ] || exit 0
LINE=$(head -1 "$Q")
sed -i '1d' "$Q" 2>/dev/null || true
eval "$LINE" >>"$B/reports/worker.log" 2>&1 || true
