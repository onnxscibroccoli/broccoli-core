\
#!/data/data/com.termux/files/usr/bin/bash
# Source from ~/.bashrc:  source ~/broccoli/tools/broccoli_rish_wire.sh
export BRO="${BRO:-$HOME/broccoli}"
brocc-ask() { "$BRO/tools/rish_grok_round.sh" "$*"; }
brocc-round() { "$BRO/tools/rish_grok_round.sh" "$*"; }
brocc-pull-last() {
  B="$(ls -t /sdcard/Broccoli/pull/bundle_* 2>/dev/null | head -1)"
  echo "$B"; test -n "$B" && cat "$B"
}
brocc-report-last() { tail -60 "$BRO/reports/rish_round.log" 2>/dev/null; tail -40 "$BRO/reports/latest.txt" 2>/dev/null; }
