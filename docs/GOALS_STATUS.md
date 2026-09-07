# Goals status (honest)

This project is **not complete**. Prior authorization does not finish
Bluetooth, Watch-Me-Do, kernel, harvest, OAuth, and virtual display.

## Usable now

- Kernel tick offline (`runtime/kernel.py`)
- Bluetooth schema + device probes
- Git sync daemon (`bin/broccoli-sync`)
- VirtualSurface + MemorySurface
- Watch-Me-Do catalog / search / authorized replay
- WatchBridge: observer events → watch steps (passwords redacted)
- Surface factory: `tools/rish_display.py` if compatible, else memory
- Kernel dry/live path: `run task <name>`

## Not done

- Full rish VirtualSurface verbs on a real display
- Feeding live UI dumps into the observer while the user taps
- Replay onto real UI (MemorySurface unless rish API matches)
- GitHub milestones M1–M10 / issue #28
- Harvest send cycle, calendar, sensors, Cloudflare production

## Will not do

- Virtual-display login / credential harvest
- CAPTCHA or rate-limit bypass
- Overwrite untracked OnDevice `tools/rish_display.py`
