#!/data/data/com.termux/files/usr/bin/bash
set -e
export PATH="$HOME/bin:$PATH"
echo "=== reboot + quarry ==="
python3 "$HOME/broccoli/reboot_bootstrap.py"
python3 "$HOME/broccoli/quarry_iter.py" 2>&1 | tee "$HOME/broccoli/reports/quarry_live.log"
echo "--- summary ---"
cat "$HOME/broccoli/reports/quarry_last.txt"
