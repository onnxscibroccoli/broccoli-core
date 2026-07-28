#!/data/data/com.termux/files/usr/bin/bash
# Run during/after a round: UI dump + input snapshot + gap report → to_chat.md
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
MSG="${1:-}"
bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
bash "$HOME/broccoli/tools/ui_snapshot_save.sh" "gap" >/dev/null
bash "$HOME/broccoli/lib/input_snapshot.sh" >/dev/null
python3 "$HOME/broccoli/tools/gap_analyze.py" "$MSG" | tee -a "$HOME/broccoli/reports/gap_watch.log"
