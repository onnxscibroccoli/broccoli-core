import os
from pathlib import Path
BRO = Path.home() / "broccoli"

def is_manual():
    return os.environ.get("BROCCOLI_MANUAL_SEND") == "1" or (BRO/"state/MANUAL_SEND").exists()
