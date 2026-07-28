#!/usr/bin/env bash
set -u
R=~/broccoli
cd "$R"
echo "=== 1 meta/cache ==="
du -sh meta/cache 2>/dev/null; ls meta/cache 2>/dev/null | wc -l
if [ -d meta/cache ]; then
  cd meta/cache
  for pat in 'FS_DISCOVERY.md_*' 'discover_directories.sh_*' 'notify_toast.sh_*' \
    'deliver_to_mac.sh_*' 'notify.sh_*' 'user_task_wait.py_*' 'toast.py_*'; do
    n=$(ls -t $pat 2>/dev/null | head -1 || true)
    [ -n "$n" ] || continue
    echo KEEP "$n"
    for f in $pat; do
      [ "$f" = "$n" ] && continue
      rm -f -- "$f" && echo DEL "$f"
    done
  done
  cd "$R"
  echo "after: $(ls meta/cache 2>/dev/null | wc -l) files"
fi
echo "=== 2 wire paths ==="
ls -la meta/inbox/from_mac meta/inbox/to_mac 2>/dev/null
ls -la inbox/from_mac 2>/dev/null || echo "no inbox/from_mac yet"
echo "=== 3 closed_loop recv/send grep ==="
grep -nE 'recv|send|from_mac|to_mac|grok_commands|inbox' lib/closed_loop.py 2>/dev/null | head -30 || echo "(no matches in closed_loop.py)"
grep -rnE 'from_mac|grok_commands|mac_ingest' lib/*.py tools/*.py 2>/dev/null | head -25
echo "=== 4 closed_loop usage ==="
python3 lib/closed_loop.py 2>&1 | head -5
echo "=== 5 recv test ==="
python3 lib/closed_loop.py recv 2>&1 | head -25
echo "=== 6 drop test file BOTH places ==="
mkdir -p meta/inbox/from_mac inbox/from_mac
cat > meta/inbox/from_mac/grok_commands.sh << 'INNER'
#!/data/data/com.termux/files/usr/bin/bash
echo WIRE_PONG
date
INNER
chmod +x meta/inbox/from_mac/grok_commands.sh
cp -f meta/inbox/from_mac/grok_commands.sh inbox/from_mac/grok_commands.sh
ls -la meta/inbox/from_mac inbox/from_mac
python3 lib/closed_loop.py recv 2>&1 | head -25
echo "=== 7 infinite loop ==="
pgrep -af broccoli_infinite_dev_loop || echo "NOT running"
tail -15 reports/infinite_nohup.log 2>/dev/null || echo "no infinite_nohup.log"
echo "=== DONE ==="
