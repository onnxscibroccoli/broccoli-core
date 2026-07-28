#!/bin/bash
# ~/broccoli/tools/broccoli_storage_healer.sh
# Safely offloads Kali datasets to SD card and prunes stale Broccoli logs

# FIXED: Using $HOME instead of ~ inside quotes
EXTERNAL_DIR="$HOME/storage/external-1/kali_data"
INTERNAL_DIR="/storage/emulated/0"

echo "[*] Initializing Broccoli Storage Healer..."

# 1. Ensure Termux storage symlinks exist
if [ ! -d "$HOME/storage/external-1" ]; then
    echo "[!] External storage 'external-1' not found."
    echo "[!] Android might not be mapping your SD card to Termux."
    echo "[!] Here is what Termux sees in your storage folder:"
    ls -l $HOME/storage
    exit 1
fi

# 2. Create the cold-storage magazine on the SD card
mkdir -p "$EXTERNAL_DIR"
echo "[*] External storage magazine ready at $EXTERNAL_DIR"

# 3. Migrate heavy datasets
mv $HOME/wordlists "$EXTERNAL_DIR/" 2>/dev/null
mv $HOME/exploits_db "$EXTERNAL_DIR/" 2>/dev/null
mv $HOME/LLM_CVE_Payloads "$EXTERNAL_DIR/" 2>/dev/null

# 4. Re-link to internal storage
ln -s "$EXTERNAL_DIR/wordlists" $HOME/wordlists 2>/dev/null
ln -s "$EXTERNAL_DIR/exploits_db" $HOME/exploits_db 2>/dev/null
ln -s "$EXTERNAL_DIR/LLM_CVE_Payloads" $HOME/LLM_CVE_Payloads 2>/dev/null

echo "[*] Kali payloads successfully symlinked to external storage."

# 5. Prune stale Broccoli UI Dumps
echo "[*] Pruning stale ui_dump.xml and wire_context.json files..."
find $HOME/broccoli -name "ui_dump*.xml" -mtime +1 -exec rm {} \;
find $HOME/tasks/broccoli-wire/queue -name "*.tmp" -mtime +1 -exec rm {} \;
rm -rf $PREFIX/tmp/* 2>/dev/null

# 6. Report freed space
FREE_SPACE=$(df -h /storage/emulated | awk 'NR==2 {print $4}')
echo "[+] Healer complete. Current internal space available: $FREE_SPACE"
