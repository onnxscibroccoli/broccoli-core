#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="${BROCCOLI_ROOT:-$HOME/broccoli}"
OUT="$B/reports/CODE_INDEX.txt"
ROOTS="$B/tools/code_roots.txt"
: > "$OUT"
while IFS= read -r root || [ -n "$root" ]; do
  [ -z "$root" ] && continue
  root="${root//\$HOME/$HOME}"
  [ -d "$root" ] || continue
  find "$root" -type f \
    ! -path '*/build/*' ! -path '*/.git/*' ! -path '*/kali-arm64/*' \
    ! -path '*/node_modules/*' ! -path '*/.gradle/*' \
    \( -name '*.kt' -o -name '*.kts' -o -name '*.py' -o -name '*.sh' \
       -o -name '*.md' -o -name '*.xml' -o -name '*.gradle' \
       -o -name 'AndroidManifest.xml' -o -name 'proguard*.pro' \) \
    2>/dev/null | while IFS= read -r f; do
      sz=$(wc -c < "$f" 2>/dev/null || echo 0)
      printf '%s\t%s\n' "$sz" "$f"
    done
done < "$ROOTS" | sort -n >> "$OUT"
echo "wrote $OUT ($(wc -l < "$OUT") files)"
