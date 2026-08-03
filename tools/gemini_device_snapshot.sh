#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT=${HOME}/broccoli-core
cd $ROOT || exit 1
OUT=$ROOT/meta/gemini/device_snapshot.md
mkdir -p $ROOT/meta/gemini
export PYTHONPATH=$ROOT
{
  echo '# Broccoli device snapshot'
  echo
  date -Is
  echo
  echo '## Git'
  git branch --show-current
  git rev-parse --short HEAD
  git status --short -- runtime/autonomy tools | head -30 || true
  echo
  echo '## Disk'
  df -h . | tail -1 || true
  echo
  echo '## goal_active'
  head -40 meta/always_on/goal_active.json 2>/dev/null || echo none
  echo
  echo '## chat_assist'
  head -50 meta/always_on/chat_assist.json 2>/dev/null || echo none
  echo
  echo '## notes'
  ls -lt meta/always_on/notes 2>/dev/null | head -8 || echo none
  echo
  echo '## health'
  python3 -c 'from runtime.governor.runtime_health_governor import RuntimeHealthGovernor as G; s=G().collect(); print(s.overall_status); [print(c.name,c.status) for c in s.components if getattr(c,"required",False)]' 2>/dev/null || echo health_fail
  echo
  echo '## issues'
  gh issue list --state open --limit 20 2>/dev/null || echo gh_fail
  echo
  echo '## files'
  ls -la runtime/autonomy/aim_ui_dump.py runtime/autonomy/chat_assist.py runtime/autonomy/dev_round.py tools/dev_round.sh 2>&1 || true
} > $OUT
echo Wrote $OUT
wc -l $OUT
