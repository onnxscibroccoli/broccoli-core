import json
import subprocess
import sys
import time
from pathlib import Path

# --- Path Configurations ---
HOME = Path.home()
ROOT = HOME / "broccoli"
LIB = ROOT / "lib"
META = ROOT / "meta"
REP = ROOT / "reports"
UI = ROOT / "ui"
BOOT = HOME / "broccoli_bootstrap.py"
CFG = ROOT / "quarry_framework.json"

# --- Core Functions ---
def toast(msg):
    """Sends a toast notification to the Android UI via Termux."""
    subprocess.run(["termux-toast", "-g", "bottom", f"{msg[:100]}"], timeout=6, capture_output=True)

def run(cmd, t=120):
    """Executes a shell command and returns the result."""
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e:
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

# --- Verification Execution ---
if __name__ == "__main__":
    print("--- Broccoli Initialization Check ---")
    print(f"Root path expected: {ROOT}")
    
    # 1. Test the run command
    print("\nTesting 'run' function...")
    result = run("echo 'Run function is working!'")
    if result.returncode == 0:
        print(f"Success. Output: {result.stdout.strip()}")
    else:
        print(f"Failed. Error: {result.stderr}")
    
    # 2. Test the toast command
    print("\nTesting 'toast' notification...")
    toast("Broccoli initialized and verified!")
    print("Check your Android screen for the toast notification.")
