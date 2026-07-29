#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH"
while true; do bash "$HOME/broccoli/tools/broccoli_supervisor.sh"; sleep 15; done
