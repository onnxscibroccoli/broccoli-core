#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

# Persistent background service
while true; do
    PYTHONPATH=. python3 runtime/main.py >> broccoli.log 2>&1 &
    PID=$!
    echo "Broccoli Governor started with PID $PID at $(date)" >> service.log
    wait $PID
    echo "Governor crashed - restarting in 5s..." >> service.log
    sleep 5
done
