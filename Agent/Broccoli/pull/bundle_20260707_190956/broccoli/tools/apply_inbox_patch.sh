#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
bash "$B/tools/version_manager.sh" snap pre_patch
for f in "$B/inbox/"*.sh "$B/inbox/patch.sh"; do
  [ -f "$f" ] || continue
  chmod +x "$f"
  bash "$f"
  mv "$f" "$B/inbox/applied_$(basename "$f").$(date +%s)" 2>/dev/null || true
done
