#!/data/data/com.termux/files/usr/bin/bash
set -e

cd ~/broccoli || exit 1

mkdir -p reports logs tmp data/harvest

echo "== Cleaning caches =="
pkg cache clean >/dev/null 2>&1 || true
apt clean >/dev/null 2>&1 || true
rm -rf ~/.cache ~/.cache/pip 2>/dev/null || true
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "== Checking chat_store.py =="

if ! grep -q "def harvest_payload" modules/chat_store.py 2>/dev/null; then
cat >> modules/chat_store.py <<'PY'

# ---- Compatibility wrapper added automatically ----
def harvest_payload(*args, **kwargs):
    """
    Backwards-compatible wrapper.
    Replace this implementation with the native one when available.
    """
    try:
        if 'harvest' in globals():
            return harvest(*args, **kwargs)
        if 'store_payload' in globals():
            return store_payload(*args, **kwargs)
        return None
    except Exception:
        return None
PY
fi

echo "== Python verification =="

python3 <<'PY'
import importlib
m=importlib.import_module("modules.chat_store")
print("Import OK")
print("harvest_payload:",hasattr(m,"harvest_payload"))
PY

echo "== Google Drive =="
rclone about gdrive: >/dev/null

REPORT=reports/status_$(date +%Y%m%d_%H%M%S).txt

{
echo "Broccoli Status"
echo "================"
date
echo
echo "PWD: $(pwd)"
echo
echo "Disk:"
df -h
echo
echo "Drive:"
rclone about gdrive:
echo
echo "Python:"
python3 - <<'PY'
import importlib
m=importlib.import_module("modules.chat_store")
print(dir(m))
PY
} > "$REPORT"

termux-clipboard-set < "$REPORT" 2>/dev/null || true

echo
echo "Done."
echo "Report: $REPORT"
echo "Status copied to Android clipboard (if Termux:API is installed)."

