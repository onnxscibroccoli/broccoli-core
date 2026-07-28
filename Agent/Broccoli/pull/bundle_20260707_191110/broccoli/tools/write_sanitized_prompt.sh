#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="${BROCCOLI_ROOT:-$HOME/broccoli}"
OUT="$B/reports/SANITIZED_PROMPT.md"
MAX="${MAX_PROMPT:-3200}"
CODE_TAIL="${CODE_TAIL:-2400}"

TASK=""
[ -s "$B/queue/agent_task.txt" ] && TASK="$(head -c 800 "$B/queue/agent_task.txt")"

ROLL=""
[ -f "$B/thread/rolling_summary.txt" ] && ROLL="$(head -c 600 "$B/thread/rolling_summary.txt")"

CONV=""
[ -f "$B/thread/conversation.jsonl" ] && CONV="$(tail -20 "$B/thread/conversation.jsonl" | head -c 2000)"
if [ -f "$B/inbox/chat_lines.txt" ]; then
  CHAT="$(tail -15 "$B/inbox/chat_lines.txt" | head -c 1200)"
  CONV="${CONV}${CONV:+$'\n'}$CHAT"
fi

CB=""
if [ -f "$B/reports/GROK_CODEBASE_FEED.md" ]; then
  CB="$(tail -c "$CODE_TAIL" "$B/reports/GROK_CODEBASE_FEED.md")"
fi

TPL="$(cat "$B/prompts/agent_turn.txt" 2>/dev/null || printf '%s\n' \
'You are helping implement features in this codebase. Use CONTEXT + CODEBASE_TAIL.
Reply with: (1) what you understood (2) concrete next steps (3) files to touch.

CONTEXT:
{{CONTEXT}}

TASK:
{{TASK}}

CODEBASE_TAIL:
{{CODE}}')"

BODY="${TPL//\{\{CONTEXT\}\}/${ROLL}
${CONV}}"
BODY="${BODY//\{\{TASK\}\}/${TASK:-Feed entire project_mythara + broccoli into Grok context; suggest implementation plan for next feature.}}"
BODY="${BODY//\{\{CODE\}\}/${CB}}"

printf '%s' "$BODY" | head -c "$MAX" > "$OUT"
