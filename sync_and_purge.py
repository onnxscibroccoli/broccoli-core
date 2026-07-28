import os, time, subprocess, glob
SRC, THRESHOLD = "/sdcard/broccoli/runs", 300
def sync_file(f):
    print(f"Syncing: {f}")
    # Trigger Android Share Intent to Drive
    subprocess.run(["am", "start", "-a", "android.intent.action.SEND", "-t", "application/json", "-d", f"file://{f}"])
    time.sleep(8) # Wait for UI interaction
    # Verify file exists on remote (simplified check)
    if os.path.exists(f): 
        os.remove(f)
        print(f"Purged: {f}")
for f in glob.glob(f"{SRC}/*.json"):
    if (time.time() - os.path.getmtime(f)) > THRESHOLD:
        sync_file(f)
