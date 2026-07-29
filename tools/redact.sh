#!/data/data/com.termux/files/usr/bin/bash
# stdin -> stdout: strip PAT-like, ssh keys, vault paths
sed -E \
  -e 's/ghp_[A-Za-z0-9_]{20,}/[REDACTED_PAT]/g' \
  -e 's/github_pat_[A-Za-z0-9_]+/[REDACTED_PAT]/g' \
  -e 's/x-access-token:[^@]+@/[REDACTED_TOKEN]@/g' \
  -e 's|'"$HOME"'/broccoli/meta/vault[^[:space:]]*|[VAULT]|g' \
  -e 's/ssh-ed25519[^[:space:]]+/[REDACTED_SSH]/g'
