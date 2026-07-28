#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
STEP=1
TOTAL=4

say(){ echo ""; echo "=============================================="; echo "  STEP $STEP of $TOTAL: $1"; echo "=============================================="; echo "$2"; echo ""; }

# STEP 1 — discovery (automatic)
say "Directory discovery (automatic)" "Scanning everything Termux can see. No input needed."
bash "$B/tools/discover_directories.sh"
bash "$B/tools/notify_toast.sh" "Wizard" "discovery done" broccoli_wiz
STEP=2

# STEP 2 — version baseline (automatic)
say "On-device version baseline (automatic)" "Creating first snapshot of tools/lib/prompts."
bash "$B/tools/version_manager.sh" snap wizard_baseline
STEP=3

# STEP 3 — GitHub optional OFF by default
if [ -f "$B/meta/vault/github_pat" ]; then
  say "GitHub vault (already done)" "PAT on device. Skipping. On-device versioning is primary."
else
  say "GitHub (OPTIONAL — skip for now)" "On-device version management is ON. You do NOT need GitHub today.
If you want GitHub later, you will run: b setup-vault
Press Enter to continue."
  read -r _
fi
STEP=4

# STEP 4 — copilot / clip instructions (clear, one-time)
say "How updates work (read this)" "
AUTOMATIC from now on:
  • Agent/copilot runs in background (if installed).
  • Before any patch: auto snapshot (versions/).

WHEN MAC SENDS A FIX — you do ONE thing only when told:
  1) Mac copies ONLY the block between BROCCOLI_START and BROCCOLI_END
  2) Phone:  b clip
     (wizard already snapshotted; clip applies safely)

OR drop a script:  ~/broccoli/inbox/patch.sh  then:  b apply

STATUS anytime:  b status
FULL DISCOVERY:  ~/broccoli/reports/FS_DISCOVERY.md

Optional — queue a copilot task:
  b task 'your instruction in plain English'
"

if [ ! -f "$B/meta/vault/github_pat" ]; then
  echo "Optional STEP (only if you want GitHub): run  b setup-vault"
fi

bash "$B/tools/notify_toast.sh" "Wizard" "complete — read STEP 4 above" broccoli_wiz
echo "WIZARD_DONE"
