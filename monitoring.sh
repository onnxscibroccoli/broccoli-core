#!/data/data/com.termux/files/usr/bin/bash
echo "=== Broccoli Core Monitoring ==="
ps aux | grep python
tail -n 20 runtime.log
echo "Uptime: $(ps -p $(cat runtime.pid 2>/dev/null) -o etime= 2>/dev/null || echo 'not running')"
