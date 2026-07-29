#!/data/data/com.termux/files/usr/bin/bash
cd ~/broccoli-core || exit 1
PYTHONPATH="$PWD" exec python3 runtime/governor/end_to_end_smoke.py --strict
