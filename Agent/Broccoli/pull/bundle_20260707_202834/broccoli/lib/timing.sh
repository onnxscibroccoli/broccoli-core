#!/data/data/com.termux/files/usr/bin/bash
tms(){ date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1000))'; }
tlog(){
  local phase="$1" t0="$2" t1
  t1=$(tms)
  echo "$(date -Iseconds) LAT ${phase} $((t1-t0))ms" >> "${B:-$HOME/broccoli}/reports/latency.log"
}
