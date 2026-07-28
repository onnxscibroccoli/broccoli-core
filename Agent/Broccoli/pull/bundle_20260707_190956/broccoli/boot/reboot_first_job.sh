#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/reboot_first.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "=== codevel_reinit $(date -Iseconds) ==="
am start -n com.termux/com.termux.app.TermuxActivity 2>/dev/null || true
sleep 1
[ -x "$HOME/aim_rish_ensure.sh" ] && bash "$HOME/aim_rish_ensure.sh" || true
printf 'id\n' | rish 2>/dev/null | head -3 || true
echo "CODEVEL_OK $(date -Iseconds)" > "$HOME/broccoli/LAST_RUN.txt"
printf '%s\n' 'ASK|Reply with one word: PONG' > "$HOME/broccoli/queue/pending.txt"
[ -x "$HOME/broccoli/tools/brocc_loop.sh" ] && pkill -f brocc_loop.sh 2>/dev/null || true
[ -x "$HOME/broccoli/tools/brocc_loop.sh" ] && nohup bash "$HOME/broccoli/tools/brocc_loop.sh" >>"$HOME/broccoli/reports/loop.log" 2>&1 &
echo "=== codevel_reinit end ==="
