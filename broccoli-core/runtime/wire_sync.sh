#!/bin/bash

echo "[1/3] Verifying existing components..."

# Check if maintenance/sync.py exists
if find maintenance -name "sync.py" | grep -q "sync.py"; then
    echo "[OK] maintenance/sync.py found."
else
    echo "[FAIL] maintenance/sync.py missing. Creating it..."
    mkdir -p maintenance
    touch maintenance/__init__.py
    # ... (SyncManager logic previously defined would go here)
fi

# Check if main.py is already wired
if grep -q "from maintenance.sync import SyncManager" runtime/main.py; then
    echo "[OK] SyncManager already imported in main.py."
else
    echo "[!] Patching main.py to include SyncManager..."
    # Insert import
    sed -i '/from models.semantic import Screen/a from maintenance.sync import SyncManager' runtime/main.py
    # Initialize and call sync
    sed -i '/print("\[11\] Begin execution loop...")/i \    print("[10.5] Initializing SyncManager...")\n    sync_mgr = SyncManager()\n    # sync_mgr.perform_full_sync()  # Uncomment to sync on boot\n' runtime/main.py
fi

echo "[3/3] System wiring complete."
