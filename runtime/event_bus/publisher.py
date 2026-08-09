#!/usr/bin/env python3

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENT_DIR = ROOT / "runtime" / "event_bus" / "processed"
EVENT_DIR.mkdir(parents=True, exist_ok=True)

def publish(source, event, detail="", severity="INFO", metadata=None):
    if metadata is None:
        metadata = {}

    payload = {
        "timestamp": int(time.time()),
        "source": source,
        "event": event,
        "severity": severity,
        "detail": detail,
        "metadata": metadata
    }

    outfile = EVENT_DIR / (
        f"{source}_{event.lower()}_{payload['timestamp']}.json"
    )

    outfile.write_text(json.dumps(payload, indent=2))
    return payload

if __name__ == "__main__":
    print(
        json.dumps(
            publish(
                "publisher",
                "SELF_TEST",
                "Event publisher operational"
            ),
            indent=2
        )
    )
