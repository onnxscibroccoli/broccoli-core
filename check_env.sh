#!/bin/bash

echo "--- Broccoli Core Environment Check ---"

# 1. Check for Git
if command -v git &> /dev/null; then
    echo "[OK] Git is installed: $(git --version)"
    if git config user.name &> /dev/null; then
        echo "     - Git identity: $(git config user.name) <$(git config user.email)>"
    else
        echo "     - [WARN] Git identity not configured."
    fi
else
    echo "[FAIL] Git is not installed. Run: pkg install git"
fi

# 2. Check for Rclone
if command -v rclone &> /dev/null; then
    echo "[OK] Rclone is installed: $(rclone --version | head -n 1)"
    REMOTES=$(rclone listremotes)
    if [ -n "$REMOTES" ]; then
        echo "     - Remotes found: $REMOTES"
    else
        echo "     - [WARN] No Rclone remotes configured. Run: rclone config"
    fi
else
    echo "[FAIL] Rclone is not installed. Run: pkg install rclone"
fi

# 3. Check for Python Environment
if command -v python &> /dev/null; then
    echo "[OK] Python is installed: $(python --version)"
else
    echo "[FAIL] Python is not installed. Run: pkg install python"
fi

echo "--- Check Complete ---"
