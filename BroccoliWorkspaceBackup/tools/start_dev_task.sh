#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
export GROK_PKG=ai.x.grok
export USE_CHROME=0
export BROCC_NO_CHROME=1
TASK="${1:-}"
if [ -z "$TASK" ] && [ -f "$HOME/broccoli/queue/pending.txt" ]; then
  TASK=$(grep -v '^#' "$HOME/broccoli/queue/pending.txt" | head -1)
fi
if [ -z "$TASK" ]; then
  TASK='ASK|Continue broccoli co-dev: UI dump only; fix rish dump_ui; implement v3/v4.1 spec; no Chrome'
fi
case "$TASK" in ASK|*) PROMPT="${TASK#ASK|}" ;; *) PROMPT="$TASK" ;; esac
bash "$HOME/broccoli/tools/toast_user.sh" "Co-dev starting — Grok native only"
am force-stop com.android.chrome 2>/dev/null || true
bash "$HOME/broccoli/tools/codevel_wire.sh" open 2>&1 | tail -5
bash "$HOME/broccoli/tools/codevel_wire.sh" in 2>&1 | tail -8 || \
  bash "$HOME/broccoli/tools/toast_user.sh" "Bring Grok to foreground, then: start-dev"
bash "$HOME/broccoli/tools/codevel_wire.sh" out "$PROMPT" 2>&1 | tail -15
bash "$HOME/broccoli/tools/codevel_wire.sh" in 2>&1 | tail -10
bash "$HOME/broccoli/tools/toast_user.sh" "Wire round done — check terminal + Grok chat"
echo DEV_TASK_STARTED
