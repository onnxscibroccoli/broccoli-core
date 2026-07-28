#!/data/data/com.termux/files/usr/bin/bash
set -u
R=~/broccoli
echo "WIRE_TEST_OK $(date -Iseconds)" >> "$R/reports/wire_test_hits.log"
echo WIRE_TEST_OK
