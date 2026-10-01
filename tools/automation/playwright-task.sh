#!/data/data/com.termux/files/usr/bin/bash
set -eu
TASK_FILE=${1:-}
if [ -z "$TASK_FILE" ] || [ ! -f "$TASK_FILE" ]; then
  echo "NOT_CONFIGURED: supply a Playwright task file" >&2
  exit 78
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "PLAYWRIGHT_MISSING: npx unavailable" >&2
  exit 79
fi
exec npx playwright test "$TASK_FILE"
