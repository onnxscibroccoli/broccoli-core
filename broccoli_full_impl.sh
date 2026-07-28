#!/usr/bin/env bash
# broccoli_full_impl.sh — paste once in Termux: maps launch, diagnoses wire, trims cache, writes report
#   bash broccoli_full_impl.sh
#   bash broccoli_full_impl.sh --apply-cache
set -u
ROOT="${BROCCOLI_ROOT:-$HOME/broccoli}"
APPLY_CACHE=0
[[ "${1:-}" == "--apply-cache" ]] && APPLY_CACHE=1
REPORT="$ROOT/docs/INVENTORY_RUN_$(date +%Y%m%d_%H%M%S).md"

log() { echo "[broccoli] $*" >&2; }

trim_meta_cache() {
  local apply="$1"
  local cache="$ROOT/meta/cache"
  [[ -d "$cache" ]] || { echo "(no meta/cache)"; return 0; }
  (
    cd "$cache"
    echo "files: $(find . -maxdepth 1 -type f | wc -l)"
    _keep() {
      local pat="$1" newest f
      newest=$(ls -t $pat 2>/dev/null | head -1 || true)
      [[ -n "$newest" ]] || return 0
      echo "KEEP $newest"
      for f in $pat; do
        [[ "$f" == "$newest" ]] && continue
        if [[ "$apply" == 1 ]]; then rm -f -- "$f" && echo "DEL $f"; else echo "WOULD_DEL $f"; fi
      done
    }
    _keep 'FS_DISCOVERY.md_*'
    _keep 'discover_directories.sh_*'
    _keep 'notify_toast.sh_*'
    _keep 'deliver_to_mac.sh_*'
    _keep 'notify.sh_*'
    _keep 'user_task_wait.py_*'
    _keep 'toast.py_*'
  )
}

install_scripts() {
  mkdir -p "$ROOT/scripts"
  cat > "$ROOT/scripts/trim_meta_cache.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${BROCCOLI_ROOT:-$HOME/broccoli}"
APPLY=0; [[ "${1:-}" == "--apply" ]] && APPLY=1
CACHE="$ROOT/meta/cache"; [[ -d "$CACHE" ]] || exit 0
cd "$CACHE"
keep(){ local p="$1" n; n=$(ls -t $p 2>/dev/null|head -1||true); [[ -n "$n" ]]||return 0
  for f in $p; do [[ "$f"=="$n" ]]&&continue
    [[ $APPLY -eq 1 ]]&&rm -f -- "$f"&&echo DEL "$f"||echo WOULD_DEL "$f"; done; }
keep FS_DISCOVERY.md_*; keep discover_directories.sh_*; keep notify_toast.sh_*
keep deliver_to_mac.sh_*; keep notify.sh_*; keep user_task_wait.py_*; keep toast.py_*'
EOF
  cat > "$ROOT/scripts/diagnose_wire.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
R="${BROCCOLI_ROOT:-$HOME/broccoli}"; cd "$R"
echo "=== wire ==="; ls -la state/infinite.lock meta/inbox/to_mac meta/inbox/from_mac 2>/dev/null
cat meta/inbox/to_mac/loop_packet.json 2>/dev/null; echo
wc -c mac/inbox.jsonl mac/processed.jsonl ui/loop_*.txt 2>/dev/null
ls -la inbox/grok_reply.txt ui/latest.xml thread/grok_last.txt 2>/dev/null
EOF
  cat > "$ROOT/scripts/map_launch_path.sh" << 'EOF'
#!/usr/bin/env bash
R="${BROCCOLI_ROOT:-$HOME/broccoli}"
head -80 "$R/bin/brocc"; echo ---; head -40 "$R/bin/wire"
grep -rn 'closed_loop\|brocc_wire\|core_round' "$R/bin" "$R/lib"/*.py 2>/dev/null | head -40 || true
EOF
  chmod +x "$ROOT/scripts/"*.sh
}

if [[ ! -d "$ROOT/lib" || ! -f "$ROOT/bin/brocc" ]]; then
  log "ERROR: expected $ROOT with lib/ and bin/brocc"
  exit 1
fi

mkdir -p "$ROOT/docs"
install_scripts

{
  echo "# Broccoli full implementation run"
  echo "- Time: $(date)"
  echo "- ROOT: $ROOT"
  echo "- apply-cache: $APPLY_CACHE"
  echo ""

  echo "## 1. Launch path"
  echo "### bin/brocc"
  echo '```'
  head -80 "$ROOT/bin/brocc" 2>/dev/null || true
  echo '```'
  echo "### bin/wire"
  echo '```'
  head -40 "$ROOT/bin/wire" 2>/dev/null || true
  echo '```'
  echo "### boot/reboot_first_job.sh"
  echo '```'
  head -40 "$ROOT/boot/reboot_first_job.sh" 2>/dev/null || true
  echo '```'
  echo "### termux boot"
  echo '```'
  ls -la ~/.termux/boot/ 2>/dev/null || echo "(none)"
  echo '```'
  echo "### grep call graph"
  echo '```'
  grep -rn 'closed_loop\|brocc_wire\|agent_loop\|broccoli_core_round\|catalog_loop' \
    "$ROOT/bin" "$ROOT/lib"/*.py 2>/dev/null | head -60 || true
  echo '```'
  echo ""

  echo "## 2. Wire diagnose"
  echo '```'
  ls -la "$ROOT/state/infinite.lock" 2>/dev/null || echo "no infinite.lock"
  ls -la "$ROOT/meta/inbox/to_mac/" "$ROOT/meta/inbox/from_mac/" 2>/dev/null || true
  echo "--- loop_packet.json ---"
  cat "$ROOT/meta/inbox/to_mac/loop_packet.json" 2>/dev/null || echo "(missing)"
  echo "--- mac ---"
  wc -c "$ROOT/mac/inbox.jsonl" "$ROOT/mac/processed.jsonl" 2>/dev/null || true
  tail -3 "$ROOT/mac/processed.jsonl" 2>/dev/null || true
  echo "--- ui loop ---"
  cat "$ROOT/ui/loop_outbox.txt" 2>/dev/null || true
  echo "--- freshness ---"
  ls -la "$ROOT/inbox/prompt.txt" "$ROOT/inbox/grok_reply.txt" \
    "$ROOT/thread/grok_last.txt" "$ROOT/ui/latest.xml" 2>/dev/null || true
  echo "--- brocc_wire refs ---"
  grep -rn 'from_mac\|to_mac\|loop_packet' "$ROOT/lib/brocc_wire.py" "$ROOT/bin/wire" 2>/dev/null | head -30 || true
  echo '```'
  echo "If grok_reply + latest.xml are fresh but from_mac empty → Mac must write meta/inbox/from_mac/."
  echo ""

  echo "## 3. Disk"
  echo '```'
  du -sh "$ROOT/meta/cache" "$ROOT/quarantine/dupes" 2>/dev/null || true
  echo "cache files: $(find "$ROOT/meta/cache" -maxdepth 1 -type f 2>/dev/null | wc -l)"
  echo '```'
  echo ""

  echo "## 4. Cache trim"
  echo '```'
  trim_meta_cache "$APPLY_CACHE"
  echo '```'
  [[ "$APPLY_CACHE" == 0 ]] && echo "_Dry-run. Run: bash broccoli_full_impl.sh --apply-cache_"
  echo ""

  echo "## 5. Helpers installed"
  echo "- $ROOT/scripts/map_launch_path.sh"
  echo "- $ROOT/scripts/diagnose_wire.sh"
  echo "- $ROOT/scripts/trim_meta_cache.sh"
  echo ""
  echo "## 6. Next"
  echo "1. Mac → phone: populate meta/inbox/from_mac/"
  echo "2. Phone loop: cd $ROOT && ./bin/brocc  (or wire)"
  echo "3. Optional: rm -rf quarantine/dupes after backup (~1.2GB)"
} | tee "$REPORT"

if [[ ! -f "$ROOT/docs/INVENTORY.md" ]]; then
  cp "$REPORT" "$ROOT/docs/INVENTORY.md"
  log "Seeded docs/INVENTORY.md from this run"
fi

log "Report saved: $REPORT"
