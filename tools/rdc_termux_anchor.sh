#!/data/data/com.termux/files/usr/bin/bash
# RDC -> Termux -> existing Rish anchor probe.
# Does not modify lib/rish_run.sh, lib/rish_cmd.sh, or lib/rish_shell.sh.
# Success is a file written by uid 2000, not an empty RC=0 from rish or am.
set -u

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export PREFIX
export HOME="${HOME:-/data/data/com.termux/files/home}"
export PATH="$PREFIX/bin:$HOME/bin:${PATH:-/system/bin:/system/xbin}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-$PREFIX/lib}"
export TMPDIR="${TMPDIR:-$PREFIX/tmp}"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u)"
OUT_DIR="$ROOT/var/rdc_anchor"
mkdir -p "$OUT_DIR" "$TMPDIR" 2>/dev/null || true

DIAG="$OUT_DIR/diag.txt"
RISH_OUT="$OUT_DIR/rish_stdout.txt"
RISH_ERR="$OUT_DIR/rish_stderr.txt"
LOCAL_ART="$OUT_DIR/RDC_TERMUX_ANCHOR.txt"
SHARED_ART="/storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt"
LOCAL_TMP_ART="/data/local/tmp/RDC_TERMUX_ANCHOR.txt"
WRAPPER="$ROOT/lib/rish_run.sh"

{
  echo "stamp=$STAMP"
  echo "caller=$(id 2>&1 || true)"
  echo "sdk_caller=$(getprop ro.build.version.sdk 2>/dev/null || true)"
  echo "home=$HOME"
  echo "prefix=$PREFIX"
  echo "path=$PATH"
  echo "ld_library_path=$LD_LIBRARY_PATH"
  echo "rish_bin=$(command -v rish 2>/dev/null || echo MISSING)"
  echo "wrapper=$WRAPPER"
  ls -l "$PREFIX/bin/rish" "$PREFIX/bin/rish_shizuku.dex" "$WRAPPER" 2>&1 || true
} > "$DIAG"

if [ ! -f "$WRAPPER" ]; then
  echo "NOT_PROVEN wrapper_missing" | tee -a "$DIAG"
  exit 2
fi

# One shell-side write. /data/data/com.termux is not a valid proof path:
# uid 2000 cannot write the Termux home, so a missing $HOME file is not a Rish failure.
INNER='{
  echo RDC_TERMUX_ANCHOR_OK
  id
  echo sdk=$(getprop ro.build.version.sdk)
} > /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt
cp /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt /data/local/tmp/RDC_TERMUX_ANCHOR.txt
id
echo sdk=$(getprop ro.build.version.sdk)
echo RDC_TERMUX_ANCHOR_OK'

set +e
bash "$WRAPPER" "$INNER" >"$RISH_OUT" 2>"$RISH_ERR"
RC=$?
set +u

echo "rish_run_rc=$RC" >> "$DIAG"
echo "--- stdout ---" >> "$DIAG"
cat "$RISH_OUT" >> "$DIAG" 2>/dev/null || true
echo "--- stderr ---" >> "$DIAG"
cat "$RISH_ERR" >> "$DIAG" 2>/dev/null || true

ART=""
if [ -f "$SHARED_ART" ]; then
  ART="$SHARED_ART"
elif [ -f "$LOCAL_TMP_ART" ]; then
  ART="$LOCAL_TMP_ART"
fi

if [ -n "$ART" ]; then
  cp "$ART" "$LOCAL_ART" 2>/dev/null || cat "$ART" > "$LOCAL_ART"
fi

echo "artifact=${ART:-MISSING}" >> "$DIAG"
if [ -z "$ART" ]; then
  echo "NOT_PROVEN no_shell_artifact" | tee -a "$DIAG"
  echo "stdout_bytes=$(wc -c < "$RISH_OUT" 2>/dev/null || echo 0)" >> "$DIAG"
  exit 3
fi

OK=0
grep -q '^RDC_TERMUX_ANCHOR_OK$' "$ART" || OK=1
grep -q 'uid=2000(shell)' "$ART" || OK=1
grep -q '^sdk=35$' "$ART" || OK=1

if [ "$OK" -ne 0 ]; then
  echo "NOT_PROVEN artifact_shape" | tee -a "$DIAG"
  echo "--- artifact ---" >> "$DIAG"
  cat "$ART" >> "$DIAG"
  exit 4
fi

echo "PASS artifact=$ART" | tee -a "$DIAG"
cat "$ART"
exit 0
