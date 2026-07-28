#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/codevel.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "=== codevel $(date -Iseconds) ==="
export BROCC_CODEVEL=1
export BROCC_IGNORE_TOS=1
bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
bash "$HOME/broccoli/lib/launch_grok_native.sh" 2>/dev/null || monkey -p ai.x.grok 1
sleep 3
bash "$HOME/broccoli/tools/dismiss_tos_grok.sh"
sleep 2
bash "$HOME/broccoli/lib/launch_grok_native.sh" 2>/dev/null || monkey -p ai.x.grok 1
sleep 4
printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\n' | rish 2>/dev/null || true
cp -f /data/local/tmp/broccoli_ui.xml "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null || true
grep -o 'package="[^"]*"' /data/local/tmp/broccoli_ui.xml 2>/dev/null | sort -u | head -5
printf '%s\n' 'ASK|Reply with one word: PONG' > "$HOME/broccoli/queue/pending.txt"
echo "CODEVEL_OK $(date -Iseconds)" > "$HOME/broccoli/LAST_RUN.txt"
echo "=== codevel end ==="
