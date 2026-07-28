\
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BRO="${BRO:-$HOME/broccoli}"
REPORT="$BRO/reports/rish_round.log"
PULL_DIR="${BROCCOLI_PULL_DIR:-/sdcard/Broccoli/pull}"
PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then
  [[ -n "${BROCCOLI_PROMPT:-}" ]] && PROMPT="$BROCCOLI_PROMPT"
  [[ -z "$PROMPT" && -f "$BRO/inbox/prompt.txt" ]] && PROMPT="$(<"$BRO/inbox/prompt.txt")"
fi
[[ -n "$PROMPT" ]] || { echo "FAIL: no prompt" >&2; exit 2; }

mkdir -p "$BRO/reports" "$BRO/inbox" "$PULL_DIR"

# === CHAT FIRST (required context) ===
FOCUS_OUT="$("$BRO/tools/chat_focus_first.sh" "${BROCCOLI_CHAT_MODE:-reuse}")" || true
echo "$FOCUS_OUT" >>"$REPORT"
echo "$FOCUS_OUT"
if ! echo "$FOCUS_OUT" | grep -q 'CHAT_FOCUS_OK'; then
  echo "FAIL: chat not focused — fix open/focus before clip" >>"$REPORT"
  echo "FAIL: chat focus" >&2
  exit 5
fi

echo "$(date -Iseconds 2>/dev/null || date) ROUND_START len=${#PROMPT}" >>"$REPORT"
printf '%s' "$PROMPT" >"$BRO/inbox/prompt.txt"

# Clip staging (codev expects it) — cleared after round
command -v termux-clipboard-set >/dev/null 2>&1 && termux-clipboard-set "$PROMPT" || true
export BRO BROCCOLI_PROMPT="$PROMPT"
cd "$BRO"
OUT="$(brocc agent codev start 2>&1)" || true
printf '%s\n' "$OUT" | tee -a "$REPORT"

BUNDLE=""
# Prefer path brocc already reported (fixes false "no bundle")
BUNDLE="$(printf '%s\n' "$OUT" | grep -E 'PULL_RISH_OK' | tail -1 | awk '{print $NF}')"
[[ -z "$BUNDLE" || ! -f "$BUNDLE" ]] && BUNDLE="$(printf '%s\n' "$OUT" | grep -oE '/sdcard/Broccoli/pull/bundle_[0-9_]+' | tail -1)"
# Wait up to 15s for file
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  [[ -n "$BUNDLE" && -f "$BUNDLE" ]] && break
  sleep 1
  BUNDLE="$(ls -t "$PULL_DIR"/bundle_* 2>/dev/null | head -1 || true)"
done

if [[ -z "$BUNDLE" || ! -f "$BUNDLE" ]]; then
  echo "$(date -Iseconds 2>/dev/null || date) FAIL no bundle dir=$PULL_DIR" >>"$REPORT"
  echo "FAIL: no bundle (pull line was in log above)" >&2
  exit 4
fi

cp -f "$BUNDLE" "$BRO/inbox/grok_last_bundle.txt"
# Normalize reply for agent (no manual copy)
python3 - "$BUNDLE" "$BRO/inbox/grok_reply.txt" <<'PYIN'
import sys, pathlib
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
text = src.read_text(encoding="utf-8", errors="replace").strip()
dst.write_text(text, encoding="utf-8")
print("wrote", dst, "bytes", len(text.encode()))
PYIN

echo "$(date -Iseconds 2>/dev/null || date) OK BUNDLE=$BUNDLE" >>"$REPORT"
echo "BUNDLE=$BUNDLE"
echo "REPLY_FILE=$BRO/inbox/grok_reply.txt"
head -c 6000 "$BRO/inbox/grok_reply.txt"
echo ""

# Unstick clipboard — do not leave prompt on clip for next cycle
command -v termux-clipboard-set >/dev/null 2>&1 && termux-clipboard-set "" || true
echo "CLIP_CLEARED" >>"$REPORT"

# Feed running agent if hook exists
if [[ -x "$BRO/tools/grok_pull_to_agent.sh" ]]; then
  "$BRO/tools/grok_pull_to_agent.sh" || true
fi
exit 0
