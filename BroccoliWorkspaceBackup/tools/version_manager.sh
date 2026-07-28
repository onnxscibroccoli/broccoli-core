#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
V="$B/versions"
M="$B/meta/version_manifest.json"
mkdir -p "$V"
cmd="${1:-help}"
label="${2:-snap}"
snap(){
  L="${1:-auto}"
  TS="$(date +%Y%m%d-%H%M%S)"
  F="$V/${TS}_${L}.tar.gz"
  tar -czf "$F" -C "$B" tools lib prompts 2>/dev/null || tar -czf "$F" -C "$B" tools 2>/dev/null
  python3 <<PY
import json, os
from pathlib import Path
B=Path.home()/"broccoli"
M=B/"meta/version_manifest.json"
d=json.loads(M.read_text()) if M.is_file() else {"current":"","history":[]}
d["history"].insert(0,{"file":"${F##*/}","ts":"$TS","label":"$L"})
d["current"]="${F##*/}"
M.write_text(json.dumps(d,indent=2))
PY
  echo "SNAP_OK $F"
  bash "$B/tools/notify_toast.sh" "Version" "snap $L" broccoli_ver
}
list_snaps(){ ls -lt "$V"/*.tar.gz 2>/dev/null | head -20 || echo "no snapshots"; cat "$M" 2>/dev/null || true; }
restore(){
  ARCH="${1:-}"
  [ -n "$ARCH" ] || { echo "usage: version restore <file.tar.gz>"; exit 1; }
  [ -f "$ARCH" ] || ARCH="$V/$ARCH"
  [ -f "$ARCH" ] || { echo "missing $ARCH"; exit 1; }
  snap "pre_restore"
  tar -xzf "$ARCH" -C "$B"
  echo "RESTORE_OK $ARCH"
  bash "$B/tools/notify_toast.sh" "Version" "restored" broccoli_ver
}
case "$cmd" in
  snap) snap "$label" ;;
  list) list_snaps ;;
  restore) restore "$label" ;;
  *) echo "version_manager.sh snap|list|restore <name>";;
esac
