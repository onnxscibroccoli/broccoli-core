#!/data/data/com.termux/files/usr/bin/bash
# Start daemons if not running. NEVER set AGENT_STOP. Safe to call from any install block.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
[ -f "$HOME/broccoli/meta/AGENT_STOP" ] && { echo "agent stopped by user (AGENT_STOP)"; exit 0; }
if ! pgrep -f 'broccoli/tools/agent_daemon.sh' >/dev/null 2>&1; then
  nohup bash "$HOME/broccoli/tools/agent_daemon.sh" >>"$HOME/broccoli/reports/agent_daemon.log" 2>&1 &
  echo "started agent_daemon pid=$!"
fi
if ! pgrep -f 'broccoli/tools/heal_supervisor.sh' >/dev/null 2>&1; then
  rm -f "$HOME/broccoli/meta/HEAL_STOP"
  nohup bash "$HOME/broccoli/tools/heal_supervisor.sh" >>"$HOME/broccoli/reports/heal_supervisor.log" 2>&1 &
  echo "started heal_supervisor pid=$!"
fi
[ -x "$HOME/broccoli/tools/notify_persistent_agent.sh" ] && bash "$HOME/broccoli/tools/notify_persistent_agent.sh" 2>/dev/null || true
