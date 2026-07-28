#!/data/data/com.termux/files/usr/bin/bash
MIN_FREE_MB="${MIN_FREE_MB:-60}"
avail_mb(){ df -k "$HOME" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'; }
disk_ok(){ [ "$(avail_mb)" -ge "$MIN_FREE_MB" ]; }
