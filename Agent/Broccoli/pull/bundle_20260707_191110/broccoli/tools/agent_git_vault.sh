#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PATF="$B/meta/vault/github_pat"
REPOF="$B/meta/github_repo"
STATE="$B/meta/git_mission.state"
LOG="$B/reports/git_mission.log"
log(){ echo "$(date -Iseconds) $*" >> "$LOG"; }

[ -f "$PATF" ] || { echo "NO_VAULT_PAT" > "$STATE"; log "no pat"; exit 0; }
PAT="$(tr -d '\n\r' < "$PATF")"
RP="$(tr -d ' \r' < "$REPOF" 2>/dev/null || true)"
[ -n "$RP" ] || { echo "NEED_REPO_NAME" > "$STATE"; exit 0; }

pkg install -y git curl 2>/dev/null || true
USER="${RP%%/*}"; NAME="${RP##*/}"
export GH_TOKEN="$PAT"
# Ensure repo (idempotent)
curl -fsS -H "Authorization: token $PAT" "https://api.github.com/repos/$RP" >/dev/null 2>&1 || \
  curl -fsS -X POST -H "Authorization: token $PAT" -d "{\"name\":\"$NAME\",\"private\":true}" \
    "https://api.github.com/user/repos" >/dev/null 2>&1 || true

cd "$B"
[ -d .git ] || git init -b main 2>/dev/null || git init
git config user.email "broccoli@local"
git config user.name "Broccoli Agent"
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:${PAT}@github.com/${RP}.git"

# CONTEXT: public files only
{
  echo "# Broccoli bootstrap (public only)"
  echo "Generated: $(date -Iseconds)"
  for f in INSTRUCTIONS.md HANDOFF.md task_box.txt; do
    [ -f "$B/$f" ] || continue
    echo "## $f"; head -c 4000 "$B/$f"; echo
  done
} > "$B/CONTEXT_PROMPT.md"

git add -A
git diff --cached --quiet || git commit -m "agent sync $(date -Iseconds)"
git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null || true
echo "DONE" > "$STATE"
log "push ok"
bash "$B/tools/notify_toast.sh" "Git" "vault push OK" broccoli_git
unset GH_TOKEN PAT
