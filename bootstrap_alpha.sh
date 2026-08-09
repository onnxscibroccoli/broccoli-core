#!/data/data/com.termux/files/usr/bin/bash
set -e

ROOT="$HOME/broccoli-core"
ALPHA="$ROOT/alpha"

mkdir -p "$ALPHA"

cd "$ALPHA"

mkdir -p \
sync \
tests \
docs \
.github/workflows \
config \
runtime \
drivers \
governor \
plugins \
storage \
metrics \
logs

cat > README.md <<'EOT'
# Broccoli Core Alpha

Production branch for the next-generation implementation.

Goals

- Android first
- Linux compatible
- Shizuku optional
- Accessibility first
- Autonomous
- Storage aware
- Incremental sync
- Event driven
- Testable
- Modular
EOT

cat > config/default.toml <<'EOT'
reserve_mb=1000
batch_files=20
batch_bytes=157286400
parallel=2
branch="alpha-testing"
EOT

cat > sync/__init__.py <<'EOT'
__version__="0.1.0-alpha"
EOT

cat > docs/ROADMAP.md <<'EOT'
Milestone 1
- Config
- State
- Inventory

Milestone 2
- Drive Adapter
- Git Adapter

Milestone 3
- Progress
- ETA
- Resume

Milestone 4
- Governor Integration

Milestone 5
- Android Packaging
EOT

cat > tests/test_bootstrap.py <<'EOT'
def test_bootstrap():
    assert True
EOT

cat > .github/workflows/python.yml <<'EOT'
name: Alpha

on:
  push:
    branches:
      - alpha-testing

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install pytest

      - run: pytest
EOT

if git rev-parse >/dev/null 2>&1; then
    git checkout -B alpha-testing || true
    git add .
    git commit -m "Bootstrap production alpha architecture" || true
fi

echo
echo "=================================="
echo " Alpha workspace created"
echo "=================================="
echo
echo "Location:"
echo "$ALPHA"
echo
echo "Next:"
echo "Implement modules incrementally."
