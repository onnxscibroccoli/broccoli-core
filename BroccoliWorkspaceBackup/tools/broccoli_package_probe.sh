#!/bin/bash
set -euo pipefail
BRO=${BRO:-$HOME/broccoli}
REG=$BRO/meta/working_registry.json
SC=$BRO/meta/package_scores.json
SL=${BROCCOLI_PROBE_SLICE:-8}
OFF=${BROCCOLI_PROBE_OFFSET:-0}
mkdir -p $BRO/meta $BRO/ui
mapfile -t C < <(pm list packages 2>/dev/null|sed 's/package://'|sort -u)
T=${#C[@]}
if [ $T -gt 0 ]; then C=("${C[@]:$OFF:$SL}"); export BROCCOLI_PROBE_OFFSET=$(( (OFF+SL)%T )); fi
python3 -c "import pathlib;pathlib.Path('$SC').parent.mkdir(parents=True,exist_ok=True);open('$SC','a').close()"
for pkg in "${C[@]}"; do
  [ -z "$pkg" ]&&continue
  sc=0; pm path "$pkg" 2>/dev/null||continue
  command -v monkey&&monkey -p "$pkg" -c android.intent.category.LAUNCHER 1 2>/dev/null&&sc=$((sc+30))||true
  sleep 1
  python3 - "$pkg" "$sc" <<'PYE'
import json,sys,datetime,pathlib
pkg,sc=sys.argv[1],int(sys.argv[2])
sp=pathlib.Path.home()/"broccoli/meta/package_scores.json"
rg=pathlib.Path.home()/"broccoli/meta/working_registry.json"
s=json.loads(sp.read_text()) if sp.exists() and sp.stat().st_size else {}
s[pkg]={"score":sc,"t":datetime.datetime.now().isoformat()}
sp.write_text(json.dumps(s,indent=2))
r=json.loads(rg.read_text())
r.setdefault("packages_tried",[])
if pkg not in r["packages_tried"]: r["packages_tried"].append(pkg)
if s:
 b=max(s.items(),key=lambda x:x[1]["score"])
 if b[1]["score"]>=70: r["chat_focus"]={"method":"probe","pkg":b[0],"score":b[1]["score"]}
rg.write_text(json.dumps(r,indent=2))
PYE
done
echo PROBE_OK
