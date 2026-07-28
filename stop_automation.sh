#!/data/data/com.termux/files/usr/bin/bash
pkill -f "autoloop.sh" 2>/dev/null && echo stopped || echo not running
command -v termux-wake-unlock >/dev/null && termux-wake-unlock || true
