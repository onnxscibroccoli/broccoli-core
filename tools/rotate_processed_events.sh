#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
DIR="\( ROOT/runtime/event_bus/processed"
KEEP=" \){1:-50}"
mkdir -p "$DIR"
python3 -c "from pathlib import Path; d=Path(\"$DIR\"); k=int(\"$KEEP\"); f=sorted(d.glob(\"*.json\"), key=lambda p: p.stat().st_mtime, reverse=True); r=f[k:];
[p.unlink(missing_ok=True) for p in r]; print(f\"kept={min(len(f),k)} removed={len(r)}\")"
