#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"; V="$B/meta/vault"; mkdir -p "$V"; chmod 700 "$V"
echo "=============================================="
echo "  OPTIONAL: GitHub PAT (device only, not Grok)"
echo "=============================================="
echo "Skip this if you use on-device versions only."
read -r -p "Continue? [y/N]: " yn
[ "$yn" = "y" ] || [ "$yn" = "Y" ] || exit 0
read -r -p "GitHub username: " GH_USER
[ -n "$GH_USER" ] || exit 1
read -r -p "Repo [broccoli-android]: " GH_REPO
GH_REPO="${GH_REPO:-broccoli-android}"
echo "Paste PAT (hidden):"
read -r -s GH_PAT; echo
printf '%s' "$GH_PAT" > "$V/github_pat"
printf '%s\n' "${GH_USER}/${GH_REPO}" > "$B/meta/github_repo"
chmod 600 "$V/github_pat"
echo "Saved. Git is optional; versions/ is primary."
