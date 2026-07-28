#!/data/data/com.termux/files/usr/bin/bash
# Usage: bash run_doc.sh path/to/file.md   OR   bash run_doc.sh path/to/file.sh
set -eu
F="${1:-}"
[ -n "$F" ] && [ -f "$F" ] || { echo "usage: run_doc.sh <file>"; exit 1; }
case "$F" in
  *.sh) bash "$F" ;;
  *.md)
    OUT="${F%.md}.run.sh"
    {
      echo '#!/data/data/com.termux/files/usr/bin/bash'
      echo 'set -eu'
      echo '# AUTO from run_doc.sh — markdown as comments + embedded blocks only'
      awk '/^```bash$/,/^```$/ { if ($0 !~ /^```/) print $0; next } { print "# " $0 }' "$F" | sed '/^# ```/d'
    } > "$OUT"
    chmod +x "$OUT"
    echo "built $OUT"
    bash "$OUT"
    ;;
  *) echo "need .md or .sh"; exit 1 ;;
esac
