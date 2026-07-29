#!/data/data/com.termux/files/usr/bin/bash
A=$(pgrep -f agent_daemon.sh | head -1 || true)
H=$(pgrep -f heal_supervisor.sh | head -1 || true)
if [ -n "$A" ]; then
  bash "$HOME/broccoli/lib/notify.sh" "Broccoli agent" "wire+rish receive ON · agent $A · heal $H" --ongoing
else
  bash "$HOME/broccoli/lib/notify.sh" "Broccoli agent" "RECOVERING — starting agent/heal" --ongoing
fi
