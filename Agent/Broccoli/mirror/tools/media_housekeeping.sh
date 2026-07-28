#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
LOG="$B/reports/media_housekeeping.log"
QUAR="$B/quarantine/dupes"
STAGE="$B/quarantine/staging"
DRY="${DRY_RUN:-1}"
DAYS="${STALE_DAYS:-7}"
TIME_MODE="${TIME_MODE:-mtime}"
MIN_FREE_MB="${MIN_FREE_MB:-80}"

log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

avail_mb(){
  df -k "$HOME" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'
}

file_mb(){
  local f="$1"
  [ -f "$f" ] || { echo 0; return; }
  stat -c%s "$f" 2>/dev/null | awk '{printf "%d", ($1+1024*1024-1)/(1024*1024)}'
}

ROOTS=(
  "$HOME/storage/shared/Download"
  "$HOME/storage/shared/DCIM"
  "$HOME/storage/shared/Pictures"
  "$HOME/storage/shared/Movies"
  "$HOME/storage/downloads"
  "$HOME/Download"
)

should_skip(){
  case "$1" in *broccoli*|*/.git/*|*/meta/vault/*) return 0;; esac
  return 1
}

find_stale_media(){
  local root="$1"
  [ -d "$root" ] || return 0
  local expr
  [ "$TIME_MODE" = "atime" ] && expr="-atime +$DAYS" || expr="-mtime +$DAYS"
  find "$root" -type f \( \
    -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \
    -o -iname '*.mp4' -o -iname '*.mov' -o -iname '*.mkv' -o -iname '*.3gp' \
  \) $expr -size +100k 2>/dev/null | while read -r f; do
    should_skip "$f" && continue
    echo "$f"
  done
}

compress_image_inplace(){
  local f="$1"
  local ext="${f##*.}"; ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
  case "$ext" in
    jpg|jpeg)
      command -v jpegoptim >/dev/null 2>&1 || return 0
      [ "$DRY" = "1" ] && { log "DRY img $f"; return 0; }
      jpegoptim --max=82 --strip-all "$f" >>"$LOG" 2>&1 && log "ok img $f"
      ;;
    png)
      command -v optipng >/dev/null 2>&1 || return 0
      [ "$DRY" = "1" ] && { log "DRY img $f"; return 0; }
      optipng -o2 -quiet "$f" >>"$LOG" 2>&1 && log "ok img $f"
      ;;
    webp)
      command -v cwebp >/dev/null 2>&1 || return 0
      [ "$DRY" = "1" ] && { log "DRY webp $f"; return 0; }
      local tmp="$STAGE/$(basename "$f").$$.webp"
      cwebp -q 80 "$f" -o "$tmp" >>"$LOG" 2>&1 && mv "$tmp" "$f" && log "ok webp $f"
      rm -f "$tmp" 2>/dev/null
      ;;
  esac
}

compress_video_space_safe(){
  local f="$1"
  command -v ffmpeg >/dev/null 2>&1 || return 0
  local sz_mb; sz_mb=$(file_mb "$f")
  local av; av=$(avail_mb)
  # Need room for staging copy briefly + growing output; after delete staging, only output remains
  local need=$(( sz_mb + MIN_FREE_MB ))
  if [ "$av" -lt "$need" ]; then
    log "SKIP video low disk: need~${need}MB avail=${av}MB file=$f"
    return 0
  fi
  if [ "$DRY" = "1" ]; then
    log "DRY video $f (${sz_mb}MB) avail=${av}MB"
    return 0
  fi
  mkdir -p "$STAGE" "$QUAR"
  local id="$$.$RANDOM"
  local staged="$STAGE/staged.$id"
  local out="$STAGE/out.$id.mp4"
  cp -f "$f" "$staged" || { log "FAIL cp $f"; return 1; }
  if ! ffmpeg -y -i "$staged" -c:v libx264 -crf 30 -preset ultrafast -c:a aac -b:a 64k "$out" >>"$LOG" 2>&1; then
    log "FAIL ffmpeg $f"
    rm -f "$staged" "$out"
    return 1
  fi
  # Free original-sized staging BEFORE moving output to final path
  rm -f "$staged"
  av=$(avail_mb)
  local out_mb; out_mb=$(file_mb "$out")
  if [ "$out_mb" -ge "$sz_mb" ]; then
    log "SKIP video not smaller: $f was ${sz_mb}MB out ${out_mb}MB — drop out"
    rm -f "$out"
    return 0
  fi
  mv "$f" "$QUAR/$(basename "$f").$id.orig" 2>/dev/null || true
  mv "$out" "$f"
  log "ok video $f ${sz_mb}MB -> ${out_mb}MB avail_now=$(avail_mb)MB"
}

dedupe_roots(){
  python3 <<'PY'
import os, hashlib, json, shutil
from pathlib import Path
from datetime import datetime

B = Path.home() / "broccoli"
LOG = B / "reports/media_housekeeping.log"
MAN = B / "reports/dedupe_manifest.jsonl"
QUAR = B / "quarantine/dupes"
DRY = os.environ.get("DRY_RUN", "1") == "1"
MIN = 50_000

roots = []
for r in [
    Path.home() / "storage/shared/Download",
    Path.home() / "storage/shared/DCIM",
    Path.home() / "storage/shared/Pictures",
    Path.home() / "storage/downloads",
]:
    if r.is_dir():
        roots.append(str(r))

skip = lambda p: "broccoli" in p or "/.git/" in p or "vault" in p

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

by_hash = {}
for root in roots:
    for dirpath, _, files in os.walk(root):
        if skip(dirpath):
            continue
        for name in files:
            p = Path(dirpath) / name
            try:
                if p.stat().st_size < MIN:
                    continue
            except OSError:
                continue
            if skip(str(p)):
                continue
            try:
                digest = sha256(p)
            except OSError:
                continue
            by_hash.setdefault(digest, []).append(p)

removed = saved = 0
for digest, paths in by_hash.items():
    if len(paths) < 2:
        continue
    paths = sorted(paths, key=lambda x: (len(str(x)), -x.stat().st_mtime))
    keep = paths[0]
    for dup in paths[1:]:
        try:
            sz = dup.stat().st_size
        except OSError:
            continue
        rec = {"ts": datetime.now().isoformat(), "keep": str(keep), "dup": str(dup), "bytes": sz, "sha256": digest[:16]}
        MAN.open("a").write(json.dumps(rec) + "\n")
        if DRY:
            print(f"DRY dedupe {dup} -> keep {keep}")
        else:
            QUAR.mkdir(parents=True, exist_ok=True)
            dest = QUAR / f"{dup.name}.{digest[:8]}"
            shutil.move(str(dup), str(dest))
            print(f"quarantined {dup}")
        removed += 1
        saved += sz

msg = f"dedupe dupes={removed} saved_bytes≈{saved} avail_check_after"
print(msg)
LOG.open("a").write(datetime.now().isoformat() + " " + msg + "\n")
PY
}

compress_stale_sorted(){
  # Images first (in-place), then videos smallest-first (less peak disk)
  local list="$STAGE/.stale_list.$$"
  : > "$list"
  for r in "${ROOTS[@]}"; do
    find_stale_media "$r" >> "$list" 2>/dev/null || true
  done
  sort -u "$list" -o "$list"
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    case "${f,,}" in
      *.mp4|*.mov|*.mkv|*.3gp) continue ;;
      *) compress_image_inplace "$f" ;;
    esac
    log "disk $(avail_mb)MB free after $f"
  done < "$list"
  # videos by size ascending
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    case "${f,,}" in
      *.mp4|*.mov|*.mkv|*.3gp) compress_video_space_safe "$f" ;;
    esac
    log "disk $(avail_mb)MB free after video"
  done < <(while IFS= read -r f; do [ -f "$f" ] && echo "$(file_mb "$f") $f"; done < "$list" | sort -n | cut -d' ' -f2-)
  rm -f "$list"
}

cmd="${1:-help}"
case "$cmd" in
  dry-run)
    export DRY_RUN=1
    log "=== dry-run avail=$(avail_mb)MB ==="
    dedupe_roots
    compress_stale_sorted
    log "=== dry-run done avail=$(avail_mb)MB ==="
    ;;
  run-low-disk)
    export DRY_RUN=0
    log "=== RUN-LOW-DISK avail=$(avail_mb)MB ==="
    dedupe_roots
    log "after dedupe avail=$(avail_mb)MB"
    compress_stale_sorted
    log "=== done avail=$(avail_mb)MB ==="
    ;;
  run)
    export DRY_RUN=0
    log "=== RUN (same as run-low-disk) ==="
    dedupe_roots
    compress_stale_sorted
    ;;
  dedupe-only)
    export DRY_RUN="${2:-1}"
    dedupe_roots
    ;;
  compress-only)
    export DRY_RUN="${2:-1}"
    compress_stale_sorted
    ;;
  *)
    echo "usage: media_housekeeping.sh dry-run | run-low-disk | run | dedupe-only [0|1] | compress-only [0|1]"
    ;;
esac
