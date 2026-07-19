#!/data/data/com.termux/files/usr/bin/bash
echo "=== Broccoli Core Runtime Starting ==="

# Pre-flight validation: check if rish is accessible in PATH
if ! command -v rish &> /dev/null; then
    echo "❌ Error: 'rish' executable not found in PATH."
    echo "   Ensure Shizuku is running and rish is exported via your profile (e.g., export PATH=\$PATH:/path/to/rish)"
    exit 1
fi

# Pre-flight validation: verify Shizuku permissions are working
if ! rish -c "id" &> /dev/null; then
    echo "❌ Error: 'rish' call failed or was denied permission."
    echo "   Please approve the Termux Shizuku prompt on your screen and re-run."
    exit 1
fi

echo "✅ Pre-flight checks passed. Launching engine..."
python3 main.py
