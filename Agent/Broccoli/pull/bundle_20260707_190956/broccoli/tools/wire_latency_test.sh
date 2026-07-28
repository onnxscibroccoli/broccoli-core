#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/latency_test.log"
T0=$(date +%s)
echo "$(date -Iseconds) LATENCY_TEST start" | tee -a "$LOG"
REPLY="$(bash "$HOME/broccoli/tools/wire_send_ui.sh" "Reply exactly one word: PHRASE_OK" 2>>"$LOG")"
T1=$(date +%s)
echo "elapsed_sec=$((T1-T0)) reply=$REPLY" | tee -a "$LOG"
echo "$REPLY"
[ "$REPLY" = "PHRASE_OK" ] && echo PASS || echo FAIL
