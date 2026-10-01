#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

OUT="${1:-$HOME/.broccoli/rish-transport-proof.txt}"
RISH_BIN="${RISH_BIN:-$(command -v rish 2>/dev/null || true)}"
mkdir -p "$(dirname "$OUT")"

if [ -z "$RISH_BIN" ] || [ ! -x "$RISH_BIN" ]; then
  echo "RISH_TRANSPORT_NOT_PROVEN: rish executable unavailable" >&2
  exit 10
fi

rm -f "$OUT"
RISH_PRESERVE_ENV=0 "$RISH_BIN" -c "echo RDC_RISH_TARGET_OK > '$OUT'; id >> '$OUT'; getprop ro.build.version.sdk >> '$OUT'" >/dev/null 2>&1
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "RISH_TRANSPORT_NOT_PROVEN: rish rc=$rc" >&2
  exit 11
fi

if [ ! -s "$OUT" ]; then
  echo "RISH_TRANSPORT_NOT_PROVEN: invocation returned rc=0 but produced no target artifact" >&2
  exit 12
fi

if ! grep -q '^RDC_RISH_TARGET_OK$' "$OUT"; then
  echo "RISH_TRANSPORT_NOT_PROVEN: target marker missing" >&2
  exit 13
fi

echo "RISH_TRANSPORT_PASS"
cat "$OUT"
