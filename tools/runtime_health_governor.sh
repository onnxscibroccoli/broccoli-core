#!/data/data/com.termux/files/usr/bin/bash
cd ~/broccoli-core || exit 1
PYTHONPATH="$PWD" exec python3 runtime/governor/runtime_health_governor.py --loop --interval 60
