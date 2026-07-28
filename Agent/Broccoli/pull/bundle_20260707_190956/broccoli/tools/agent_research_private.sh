#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
bash "$B/tools/notify_toast.sh" "Research" "local…" broccoli_research
for s in investigate_system.sh gap_watch.sh; do
  [ -x "$B/tools/$s" ] && bash "$B/tools/$s" >>"$B/reports/research_private.log" 2>&1 || true
done
bash "$B/tools/notify_toast.sh" "Research" "done (private log)" broccoli_research
