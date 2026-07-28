#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/TERMUX_DISK_REPORT.md"
TS="$(date -Iseconds)"

avail_k(){ df -k "$1" 2>/dev/null | awk 'NR==2{print $4}'; }
human(){ awk -v k="$1" 'BEGIN{printf "%.1fG", k/1024/1024}'; }

{
  echo "# Termux disk investigation"
  echo "Generated: $TS"
  echo ""
  echo "## Summary"
  echo "- HOME=$HOME"
  echo "- PREFIX=${PREFIX:-/data/data/com.termux/files/usr}"
  echo ""
  AV=$(avail_k "$HOME")
  echo "- Avail on HOME fs: $(human "$AV") ($(avail_k "$HOME") KB)"
  df -h "$HOME" 2>/dev/null | tail -1 | awk '{print "- df: "$0}'
  echo ""

  echo "## Top-level HOME (du -sh each entry)"
  for x in "$HOME"/* "$HOME"/.[!.]* 2>/dev/null; do
    [ -e "$x" ] || continue
    du -sh "$x" 2>/dev/null || true
  done | sort -hr | head -40
  echo ""

  echo "## PREFIX top (Termux packages — often huge)"
  P="${PREFIX:-/data/data/com.termux/files/usr}"
  if [ -d "$P" ]; then
    du -sh "$P" 2>/dev/null || true
    for x in "$P"/*; do
      [ -d "$x" ] || continue
      du -sh "$x" 2>/dev/null
    done | sort -hr | head -25
  fi
  echo ""

  echo "## broccoli breakdown"
  if [ -d "$B" ]; then
    du -sh "$B" 2>/dev/null
    for x in versions quarantine reports thread inbox meta tools lib sandbox; do
      [ -d "$B/$x" ] && du -sh "$B/$x" 2>/dev/null
    done
    echo "### versions (newest 10)"
    ls -lt "$B/versions"/*.tar.gz 2>/dev/null | head -10 || echo "(none)"
    echo "### quarantine"
    du -sh "$B/quarantine"/* 2>/dev/null | sort -hr | head -15 || true
    echo "### largest files under broccoli (top 30)"
    find "$B" -type f -size +1M 2>/dev/null -exec du -h {} \; | sort -hr | head -30
  fi
  echo ""

  echo "## Package / build caches"
  for d in \
    "$P/var/cache/apt/archives" \
    "$P/var/cache/pkg" \
    "$HOME/.cache" \
    "$HOME/.cache/pip" \
    "$HOME/go/pkg" \
    "$HOME/.npm" \
    "$HOME/.cargo/registry" \
    "$HOME/.rustup" \
    "$HOME/.local/share/Trash" \
  ; do
    [ -d "$d" ] && echo "- $d: $(du -sh "$d" 2>/dev/null | awk '{print $1}')"
  done
  echo ""

  echo "## Largest files under HOME (>=5MB, top 40)"
  find "$HOME" -xdev -type f -size +5M 2>/dev/null \
    ! -path "*/broccoli/meta/vault/*" \
    -exec du -h {} \; 2>/dev/null | sort -hr | head -40
  echo ""

  echo "## Installed packages (count + heavy hints)"
  pkg list-installed 2>/dev/null | wc -l | awk '{print "- package count: "$1}'
  for heavy in golang rust ffmpeg llvm nodejs python; do
    pkg list-installed 2>/dev/null | grep -qi "^$heavy" && echo "- has package matching: $heavy"
  done
  echo ""

  echo "## Recommendations (read-only — run b termux-clean dry first)"
  echo "1. \`pkg clean -y\` — apt/pkg download cache"
  echo "2. Trim \`~/broccoli/versions/*.tar.gz\` (keep newest 2)"
  echo "3. Empty \`~/broccoli/quarantine/staging\` after failed compress"
  echo "4. Truncate large \`~/broccoli/reports/*.log\`"
  echo "5. Remove unused heavy packages: \`pkg uninstall <name>\` only after you confirm"
  echo "6. \`pip cache purge\` if pip cache is large"
  echo "7. Phone Settings → Apps → Termux → Storage (Android-side cache, not this script)"
} > "$OUT"

echo "Wrote $OUT"
wc -c "$OUT"
