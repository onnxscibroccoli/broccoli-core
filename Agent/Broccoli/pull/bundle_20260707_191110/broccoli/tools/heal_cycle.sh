#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
bash "$HOME/broccoli/tools/notify_persistent_agent.sh"
[ -f "$HOME/broccoli/meta/AGENT_STOP" ] || {
  pgrep -f agent_daemon.sh >/dev/null 2>&1 || nohup bash "$HOME/broccoli/tools/agent_daemon.sh" >>"$HOME/broccoli/reports/agent_daemon.log" 2>&1 &
}
grep -q 'package="ai.x.grok"' "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null || bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
bash "$HOME/broccoli/tools/notify_persistent_agent.sh"
