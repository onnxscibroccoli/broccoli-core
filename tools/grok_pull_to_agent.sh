\
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BRO="${BRO:-$HOME/broccoli}"
REPLY="$BRO/inbox/grok_reply.txt"
TASK="$BRO/tasks/current/TASK.md"
[[ -f "$REPLY" ]] || { echo "no grok_reply.txt"; exit 1; }
# Agent-visible state (no human paste)
{
  echo "=== GROK_PULL $(date -Iseconds 2>/dev/null || date) ==="
  cat "$REPLY"
  echo "=== END GROK_PULL ==="
} >> "$BRO/reports/agent_feed.log"
# Append to research notes if pilot task
if [[ -f "$TASK" ]] && grep -qi deep-research "$TASK" 2>/dev/null; then
  echo "" >> "$BRO/research/notes.md"
  echo "## $(date -Iseconds 2>/dev/null || date)" >> "$BRO/research/notes.md"
  head -c 8000 "$REPLY" >> "$BRO/research/notes.md"
fi
# One agent tick to consume inbox (your build)
export BRO
if command -v brocc >/dev/null 2>&1; then
  brocc agent-loop-once 2>&1 | tee -a "$BRO/reports/agent_feed.log" || true
fi
echo "AGENT_FEED_OK"
