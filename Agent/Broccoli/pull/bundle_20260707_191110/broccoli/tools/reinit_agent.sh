#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
[ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/reinit.log" 2>&1 || true
pkill -f 'collab_rish_loop|broccoli-daemon|broccoli_worker|watchdog|ui_worker|grok_copilot|agent_handler' 2>/dev/null || true
sleep 2
rm -f "$B/meta/AGENT_STOP" "$B/meta/AGENT_STOP_REQUESTED"
if [ -f "$B/tools/reboot_bootstrap.py" ]; then
  python3 "$B/tools/reboot_bootstrap.py" >>"$B/reports/reinit.log" 2>&1
else
  nohup bash "$B/tools/broccoli-daemon.sh" >>"$B/reports/daemon.log" 2>&1 &
fi
sleep 2
pgrep -af 'collab_rish_loop|broccoli-daemon|watchdog' || true
df -h "$HOME" | tail -1
