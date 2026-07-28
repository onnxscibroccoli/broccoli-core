#!/data/data/com.termux/files/usr/bin/bash
# End of ANY broccoli install: ensure agent stays up — no pkill, no AGENT_STOP, no blocking wire test.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
rm -f "$HOME/broccoli/meta/AGENT_STOP"
bash "$HOME/broccoli/tools/agent_ensure_running.sh"
echo "AGENT_PERSIST_OK — daemon waiting for queue or Grok chat dump"
