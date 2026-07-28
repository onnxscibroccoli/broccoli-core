#!/data/data/com.termux/files/usr/bin/bash
for R in "${RISH_BIN:-}" "$PREFIX/bin/rish" "$HOME/rish/rish"; do
  [ -n "$R" ] && [ -x "$R" ] && exec "$R" "$@"
done
echo "rish missing" >&2; exit 127
