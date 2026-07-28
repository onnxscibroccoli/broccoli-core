#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
bash "$B/ui_pull.sh" || exit 1
python3 "$B/ui_window_check.py" >/dev/null || exit 1
