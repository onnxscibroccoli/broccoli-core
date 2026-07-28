#!/data/data/com.termux/files/usr/bin/bash
cd \~/broccoli
while true; do
  if ! pgrep -f autoloop.sh > /dev/null; then
    nohup ./autoloop.sh > /dev/null 2>&1 &
    echo $! > reports/daemon.pid
  fi
  sleep 10
done
