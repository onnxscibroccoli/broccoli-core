#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/DEVICE_OUTPUT_FOR_MAC.txt"
PKG=""; [ -f "$B/reports/ui_dump.xml" ] && PKG="$(grep -o 'package="[^"]*"' "$B/reports/ui_dump.xml" | head -1 || true)"
Q="$(wc -l < "$B/queue/missions.txt" 2>/dev/null || echo 0)"
GPH="$(cat "$B/meta/git_mission.state" 2>/dev/null || echo none)"
LAST="$(tail -1 "$B/thread/grok_last.txt" 2>/dev/null | head -c 80 || true)"
{
  echo "===== DEVICE_OUTPUT $(date -Iseconds) ====="
  echo "git_phase=$GPH missions_queued=$Q"
  echo "ui_pkg=${PKG:-none}"
  echo "grok_last_prefix=${LAST}"
  echo "daemons:"; pgrep -af 'agent_handler|agent_daemon' 2>/dev/null | head -3 || true
  echo "===== END ====="
} | bash "$B/tools/redact.sh" > "$OUT"
