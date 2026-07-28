#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LIVE=0
for a in "$@"; do [ "$a" = "--live" ] && LIVE=1; done
echo "=== Broccoli investigate $(date -Iseconds) ==="
pgrep -af wire_daemon 2>/dev/null || echo "(no wire_daemon)"
[ -f "$HOME/broccoli/meta/WIRE_STOP" ] && echo "WIRE_STOP set" || echo "WIRE_STOP clear"
if [ "$LIVE" -eq 1 ]; then
  python3 "$HOME/broccoli/tools/investigate_system.py" --live | tee "$HOME/broccoli/reports/investigate_last_stdout.txt"
else
  python3 "$HOME/broccoli/tools/investigate_system.py" --no-live | tee "$HOME/broccoli/reports/investigate_last_stdout.txt"
fi
echo ""
echo "Wrote: ~/broccoli/reports/INVESTIGATION_REPORT.md"
echo "Wrote: ~/broccoli/reports/investigation.json"
echo "Wrote: ~/broccoli/meta/codev_window.json"
echo "Co-dev: cat ~/broccoli/reports/INVESTIGATION_REPORT.md"
