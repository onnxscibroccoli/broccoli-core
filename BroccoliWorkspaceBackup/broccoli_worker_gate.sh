#!/data/data/com.termux/files/usr/bin/bash
set -eu
LOCK="$HOME/broccoli/meta/worker.lock"
mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK" || exit 0
flock -n 9 || exit 0
export PATH="$HOME/broccoli/bin:$PATH"
export PYTHONPATH="$HOME/broccoli/lib${PYTHONPATH:+:$PYTHONPATH}"
# BROCC_DISPLAY_LANE
if command -v python3 >/dev/null && test -x "$HOME/broccoli_secondary_display.py" 2>/dev/null; then
  if python3 "$HOME/broccoli_secondary_display.py" may-run 2>/dev/null | grep -q no; then
    python3 "$HOME/broccoli_secondary_display.py" defer grok_job 2>/dev/null || true
    brocc research round 2>/dev/null || true
    exit 0
  fi
fi
if test -f "$HOME/broccoli_worker.sh"; then
  exec bash "$HOME/broccoli_worker.sh" "$@"
fi
echo "no worker body" >&2
exit 1
