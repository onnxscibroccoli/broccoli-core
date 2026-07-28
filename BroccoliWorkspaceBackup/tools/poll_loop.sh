#!/bin/bash
set -u
BRO=${BRO:-$HOME/broccoli}
LOG=$BRO/reports/poll_loop.log
P=${BROCCOLI_POLL_SEC:-90}
export BRO
mkdir -p $BRO/reports $BRO/inbox
if [ -f $BRO/meta/working_registry.json ]; then
  export BROCCOLI_GROK_PKG="$(python3 -c "import json;print(json.load(open('$BRO/meta/working_registry.json')).get('chat_focus',{}).get('pkg') or '')" 2>/dev/null||true)"
fi
while true; do
  echo "$(date -Iseconds 2>/dev/null || date) POLL_TICK">>$LOG
  PROMPT=$(cat $BRO/inbox/prompt.txt 2>/dev/null||true)
  [ -z "$PROMPT" ]&&PROMPT='BROCC_POLL: one improvement; reply LOOP_OK'
  [ -x $BRO/brocc-fix ]&&$BRO/brocc-fix ask "$PROMPT">>$LOG 2>&1||true
  [ -x $BRO/tools/rish_grok_round.sh ]&&$BRO/tools/rish_grok_round.sh "$PROMPT">>$LOG 2>&1||true
  [ -x $BRO/tools/grok_pull_to_agent.sh ]&&$BRO/tools/grok_pull_to_agent.sh>>$LOG 2>&1||true
  command -v brocc&&brocc agent-loop-once>>$LOG 2>&1||true
  [ -f $BRO/tools/broccoli_conv_archive.py ]&&python3 $BRO/tools/broccoli_conv_archive.py --ingest>>$LOG 2>&1||true
  python3 -c "import json,datetime,sys; d=json.load(open(sys.argv[1])); d['last_good_round']=datetime.datetime.now().isoformat(); json.dump(d,open(sys.argv[1],'w'),indent=2)" "$BRO/meta/working_registry.json" 2>/dev/null||true
  sleep $P
done
