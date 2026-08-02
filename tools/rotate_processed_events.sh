#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
DIR="$ROOT/runtime/event_bus/processed"
KEEP="${1:-50}"
mkdir -p "$DIR"
python3 - "$DIR" "$KEEP" <<'END'
import sys
from pathlib import Path
d = Path(sys.argv[1])
keep_n = int(sys.argv[2])
files = sorted(d.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
drop = files[keep_n:]
for p in drop:
    p.unlink(missing_ok=True)
print(f'processed rotation: kept={min(len(files), keep_n)} removed={len(drop)}')
END
