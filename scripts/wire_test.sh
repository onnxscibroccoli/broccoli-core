#!/usr/bin/env bash
set -u
R=~/broccoli
cd "$R"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$R/reports/wire_test_$TS.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== WIRE TEST $TS ==="

echo "--- A. Inboxes ---"
ls -la meta/inbox/from_mac meta/inbox/to_mac 2>/dev/null
ls -la inbox/from_mac 2>/dev/null || true
echo "--- loop_packet ---"
cat meta/inbox/to_mac/loop_packet.json 2>/dev/null || echo "(missing)"

echo "--- B. Install test command (phone-only, no Mac) ---"
mkdir -p meta/inbox/from_mac inbox/from_mac
cat > meta/inbox/from_mac/grok_commands.sh << 'INNER'
#!/data/data/com.termux/files/usr/bin/bash
set -u
R=~/broccoli
echo "WIRE_TEST_OK $(date -Iseconds)" >> "$R/reports/wire_test_hits.log"
echo WIRE_TEST_OK
INNER
chmod +x meta/inbox/from_mac/grok_commands.sh
cp -f meta/inbox/from_mac/grok_commands.sh inbox/from_mac/grok_commands.sh
ls -la meta/inbox/from_mac/grok_commands.sh inbox/from_mac/grok_commands.sh

echo "--- C. Manual run (proves script is valid) ---"
bash meta/inbox/from_mac/grok_commands.sh
tail -3 reports/wire_test_hits.log 2>/dev/null || true

echo "--- D. closed_loop ---"
python3 lib/closed_loop.py 2>&1 | head -8
echo "recv:"
python3 lib/closed_loop.py recv 2>&1 | head -30
echo "once:"
python3 lib/closed_loop.py once 2>&1 | head -30

echo "--- E. After recv/once: files still there? ---"
ls -la meta/inbox/from_mac inbox/from_mac 2>/dev/null

echo "--- F. Who references from_mac? ---"
grep -rn 'from_mac\|grok_commands\|mac_ingest' lib tools 2>/dev/null | head -30

echo "--- G. Infinite loop ---"
pgrep -af broccoli_infinite_dev_loop || echo "NOT running"
tail -10 reports/infinite_nohup.log 2>/dev/null || true

echo "--- H. Freshness ---"
ls -la inbox/grok_reply.txt inbox/prompt.txt thread/grok_last.txt ui/latest.xml 2>/dev/null

echo "=== END ==="
echo "Log: $LOG"
