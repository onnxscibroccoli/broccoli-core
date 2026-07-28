#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH"
L="$HOME/broccoli/reports/supervisor.log"
log(){ echo "$(date -Iseconds) $*" >>"$L"; }
pgrep -f "broccoli/tools/broccoli_brain.py" >/dev/null || { nohup python3 "$HOME/broccoli/tools/broccoli_brain.py" >>"$HOME/broccoli/reports/daemon.log" 2>&1 &; log START brain; }
pgrep -f "broccoli/tools/ui_dump_loop.py" >/dev/null || { nohup python3 "$HOME/broccoli/tools/ui_dump_loop.py" >>"$HOME/broccoli/reports/daemon.log" 2>&1 &; log START dump; }
