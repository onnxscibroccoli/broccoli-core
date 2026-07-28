#!/usr/bin/env python3
import json, time
from pathlib import Path

ROOT = Path.home() / "broccoli"

def main():
    import sys
    sys.path.insert(0, str(ROOT / "lib"))
    from idle_takeover import wait_idle_then_grok_takeover
    policy = json.loads((ROOT / "meta" / "idle_policy.json").read_text())
    gap = int(policy.get("between_cycles_sec", 25))
    print("idle daemon: 10s inactive → Grok takeover", flush=True)
    while True:
        try:
            wait_idle_then_grok_takeover()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("err", e, flush=True)
        time.sleep(gap)

if __name__ == "__main__":
    main()
