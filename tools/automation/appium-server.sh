#!/data/data/com.termux/files/usr/bin/bash
set -eu
if ! command -v npx >/dev/null 2>&1; then
  echo "APPIUM_MISSING: npx unavailable" >&2
  exit 79
fi
if ! npx --no-install appium --version >/dev/null 2>&1; then
  echo "APPIUM_MISSING: install Appium explicitly before enabling service" >&2
  exit 78
fi
exec npx --no-install appium server --address 127.0.0.1 --port "${APPIUM_PORT:-4723}"
