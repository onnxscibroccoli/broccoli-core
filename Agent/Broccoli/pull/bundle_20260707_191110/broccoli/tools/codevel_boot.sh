#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
pkill -f brocc_loop.sh 2>/dev/null || true
bash "$HOME/broccoli/boot/reboot_first_job.sh" 2>/dev/null || true
bash "$HOME/broccoli/tools/grok_foreground_then.sh" status
bash "$HOME/broccoli/tools/grok_foreground_then.sh" pong
echo CODEVEL_BOOT_OK see ~/broccoli/reports/foreground.log
