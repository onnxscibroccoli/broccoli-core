#!/bin/bash
set -euo pipefail
BRO=${BRO:-$HOME/broccoli}
L=$BRO/reports/heal_supervisor.log
start_one(){ n=$1; x=$2; pgrep -f "$x"&&return 0; nohup bash "$x">>$L 2>&1&; echo START $n>>$L; }
case ${1:-} in
 start) mkdir -p $BRO/reports; start_one heal $BRO/tools/heal_daemon.sh; start_one poll $BRO/tools/poll_loop.sh; echo SUPERVISOR_OK;;
 stop) pkill -f heal_daemon.sh||true; pkill -f poll_loop.sh||true; echo SUPERVISOR_STOP;;
 status) pgrep -af heal_daemon.sh||true; pgrep -af poll_loop.sh||echo none;;
 *) echo usage start stop status; exit 1;;
esac
