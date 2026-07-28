#!/usr/bin/env python3
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path.home() / "broccoli/lib"))
from smoke_autoheal import heal_smoke
def main():
    sm = heal_smoke()
    print(json.dumps({"smoke": sm}, indent=2))
    return 0 if sm.get("status") == "PASS" else 1
if __name__ == "__main__":
    sys.exit(main())
