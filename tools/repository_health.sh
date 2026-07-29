#!/data/data/com.termux/files/usr/bin/bash
cd ~/broccoli-core || exit 1
PYTHONPATH="$PWD" python3 runtime/health/repository_health.py
