#!/data/data/com.termux/files/usr/bin/bash
# Push gap summary to Grok via queue (accessibility layer), truncated.
set -eu
TO="$HOME/broccoli/thread/to_chat.md"
Q="$HOME/broccoli/queue/pending.txt"
[ -f "$TO" ] || { echo "no to_chat.md"; exit 1; }
BODY="$(sed -n '1,35p' "$TO" | tr '\n' ' ' | sed 's/  */ /g' | head -c 900)"
printf '%s\n' "ASK|BROCCOLI_GAP: $BODY" >> "$Q"
echo "enqueued gap ASK (${#BODY} chars)"
