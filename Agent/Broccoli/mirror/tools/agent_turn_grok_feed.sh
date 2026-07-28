#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="${BROCCOLI_ROOT:-$HOME/broccoli}"
echo "Build codebase feed for Grok (this may take a minute)..."
MAX_BYTES="${MAX_BYTES:-1200000}" "$B/tools/build_grok_feed.sh"
"$B/tools/write_sanitized_prompt.sh"
echo "---"
echo "1) Paste into Grok: $B/reports/GROK_CODEBASE_FEED.md (or upload if supported)"
echo "2) Then paste short turn: $B/reports/SANITIZED_PROMPT.md"
echo "3) Set task anytime: echo 'your feature' > $B/queue/agent_task.txt"
