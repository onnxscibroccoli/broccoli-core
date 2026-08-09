#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$HOME/broccoli-core"

touch .gitignore

append() {
grep -qxF "$1" .gitignore || echo "$1" >> .gitignore
}

echo "Updating .gitignore..."

append ""
append "# Runtime state"
append "tools/sync_state.json"

append ""
append "# Generated notification cache"
append "meta/notif_mine/"

append ""
append "# Generated research"
append "reports/research/"

append ""
append "# Runtime logs"
append "*.log"
append "*.pid"

git add .gitignore

git commit -m "Ignore runtime-generated files" || true

echo
echo "Repository hygiene complete."
echo
git status --short
