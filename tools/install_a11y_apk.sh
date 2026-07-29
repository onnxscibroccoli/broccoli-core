#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export BRO="${BRO:-$HOME/broccoli}"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
export PYTHONPATH="$BRO/lib"
PKG="${BROCCOLI_A11Y_PKG:-ai.broccoli.a11y}"

# Look for APK (you must place ONE of these)
CANDIDATES=(
  "$BRO/a11y-apk/broccoli-a11y-debug.apk"
  "$BRO/a11y-apk/app-debug.apk"
  "/sdcard/Download/broccoli-a11y-debug.apk"
  "/sdcard/Download/app-debug.apk"
)
APK=""
for f in "${CANDIDATES[@]}"; do
  if [[ -f "$f" ]]; then APK="$f"; break; fi
done

if [[ -z "$APK" ]]; then
  echo "NO_APK_FOUND"
  echo "Put debug APK at one of:"
  printf '  %s\n' "${CANDIDATES[@]}"
  echo ""
  echo "Build on a PC (once), then copy to phone USB / Downloads:"
  echo "  cd broccoli/a11y-apk && ./gradlew assembleDebug"
  echo "  => a11y-apk/app/build/outputs/apk/debug/app-debug.apk"
  echo "  rename/copy to: ~/broccoli/a11y-apk/broccoli-a11y-debug.apk"
  exit 1
fi

echo "INSTALLING $APK"
python3 <<PY
import os, subprocess, shutil
from pathlib import Path
apk = Path("$APK").resolve()
bro = Path.home() / "broccoli"
sys_apk = bro / "a11y-apk" / "_install.apk"
sys_apk.write_bytes(apk.read_bytes())
# Rish shell sees /data/local/tmp reliably
cmd = f"cp {sys_apk} /data/local/tmp/broccoli_a11y.apk && pm install -r -g /data/local/tmp/broccoli_a11y.apk"
env = os.environ.copy()
env["RISH_APPLICATION_ID"] = os.environ.get("RISH_APPLICATION_ID", "com.termux")
rish = shutil.which("rish") or str(Path(os.environ["PREFIX"]) / "bin/rish")
p = subprocess.run([rish, "-c", cmd], capture_output=True, text=True, timeout=120, env=env)
print(p.stdout or "")
print(p.stderr or "")
raise SystemExit(p.returncode)
PY

python3 -c "
import sys; sys.path.insert(0,'$BRO/lib')
from broccoli_a11y_rish import a11y_installed, open_accessibility_settings
print('installed_after=', a11y_installed())
if a11y_installed():
    print('NEXT: Settings → Accessibility → Broccoli A11y Helper → ON')
    open_accessibility_settings()
"
