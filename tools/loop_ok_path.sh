#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
export BROCCOLI_GROK_PKG="${BROCCOLI_GROK_PKG:-ai.x.grok}"
APP="${BROCC_CHAT_APP:-grok}"
TASK="${1:-BROCC_TASK reply exactly: LOOP_OK}"
WAIT="${BROCCOLI_REPLY_WAIT:-40}"
LOG="$HOME/broccoli/reports/loop_ok_path.log"
BRO="$HOME/broccoli"
ts(){ date -Iseconds; }
echo "$(ts) === loop_ok_path start app=$APP ===" >>"$LOG"

bash "$HOME/aim_rish_ensure.sh" >>"$LOG" 2>&1 || { echo "$(ts) step0 rish fail" >>"$LOG"; exit 2; }

echo "$(ts) step1 foreground" >>"$LOG"
bash "$BRO/lib/shizuku_apps.sh" "$APP" foreground >>"$LOG" 2>&1

echo "$(ts) step2 send" >>"$LOG"
bash "$BRO/tools/a11y_send_round.sh" "$TASK" >>"$LOG" 2>&1 || true
if command -v brocc >/dev/null; then brocc autoheal >>"$LOG" 2>&1 || true; fi

echo "$(ts) step3 wait ${WAIT}s" >>"$LOG"
sleep "$WAIT"

echo "$(ts) step4 recv" >>"$LOG"
bash "$BRO/tools/consume_response.sh" >>"$LOG" 2>&1 || true
REPLY="$(cat "$BRO/inbox/grok_reply.txt" 2>/dev/null || true)"
if echo "$REPLY" | grep -qi LOOP_OK; then
  echo "$(ts) === LOOP_OK PASS ===" >>"$LOG"
  echo LOOP_OK_PASS
  exit 0
fi
echo "$(ts) LOOP_OK FAIL snippet=${REPLY:0:120}" >>"$LOG"
echo LOOP_OK_FAIL
exit 1
