#!/data/data/com.termux/files/usr/bin/bash
echo "=== Broccoli Core Service ==="
pkill -f "python3 main.py" 2>/dev/null || true
nohup /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/broccoli-core/runtime/main.py > runtime.log 2>&1 &
echo $! > runtime.pid
echo "✅ Service started (PID $(cat runtime.pid))"
