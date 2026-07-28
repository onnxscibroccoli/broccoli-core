#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="${BROCCOLI_ROOT:-$HOME/broccoli}"
OUT="$B/reports/GROK_CODEBASE_FEED.md"
MAX_BYTES="${MAX_BYTES:-1200000}"   # ~1.2MB; lower if Grok paste chokes
INDEX="$B/reports/CODE_INDEX.txt"

"$B/tools/build_code_index.sh"

{
  echo "# Codebase feed for Grok"
  echo "Generated: $(date -Iseconds 2>/dev/null || date)"
  echo ""
  echo "## File index (path, bytes)"
  echo '```'
  awk '{print $2 "\t" $1}' "$INDEX" | head -500
  echo '```'
  echo ""
  echo "## File contents (priority: agent, minimax, tools, docs/wiki)"
} > "$OUT"

# Priority order: small agent surface first, then expand
PRIORITY_RE='AgentLoop|StreamingChat|ToolRegistry|AgentRunner|minimax/|agent/tools/|docs/wiki/|broccoli/'

total=0
add_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  local sz h body
  sz=$(wc -c < "$f")
  h=$(( sz + 80 ))
  [ "$(( total + h ))" -gt "$MAX_BYTES" ] && return 1
  {
    echo ""
    echo "### $f"
    echo '```'
    head -c 80000 "$f"
    echo '```'
  } >> "$OUT"
  total=$(( total + h ))
  return 0
}

# Pass 1: priority paths
while IFS=$'\t' read -r _ f; do
  echo "$f" | grep -qE "$PRIORITY_RE" || continue
  add_file "$f" || break
done < "$INDEX"

# Pass 2: everything else by size (smallest first)
while IFS=$'\t' read -r _ f; do
  echo "$f" | grep -qE "$PRIORITY_RE" && continue
  add_file "$f" || break
done < "$INDEX"

echo "wrote $OUT ($(wc -c < "$OUT") bytes, cap $MAX_BYTES)"
