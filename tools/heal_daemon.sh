#!/bin/bash
set -u
BRO=${BRO:-$HOME/broccoli}
LOG=$BRO/reports/heal_daemon.log
INT=${BROCCOLI_HEAL_INTERVAL:-45}
mkdir -p $BRO/reports $BRO/meta
while true; do
  echo "$(date -Iseconds 2>/dev/null || date) HEAL_TICK">>$LOG
  export BRO=$HOME/broccoli
  [ -x $BRO/tools/chat_focus_first.sh ]&&$BRO/tools/chat_focus_first.sh reuse>>$LOG 2>&1||true
  command -v brocc&&brocc clip-test>>$LOG 2>&1||true
  command -v brocc&&brocc autoheal>>$LOG 2>&1||true
  [ -f $BRO/broccoli_meta_heal.py ]&&python3 $BRO/broccoli_meta_heal.py>>$LOG 2>&1||true
  [ -x $BRO/tools/broccoli_package_probe.sh ]&&timeout 120 bash $BRO/tools/broccoli_package_probe.sh slice>>$LOG 2>&1||true
  [ -f $BRO/tools/broccoli_conv_archive.py ]&&python3 $BRO/tools/broccoli_conv_archive.py --maintain>>$LOG 2>&1||true
  sleep $INT
done
