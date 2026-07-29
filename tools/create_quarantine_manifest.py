#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime, timezone

REPORT = Path("reports")

reachable = set(
    json.loads(
        (REPORT/"runtime_reachable_modules.json").read_text()
    )
)

candidates = json.loads(
    (REPORT/"quarantine_candidates.json").read_text()
)


manifest = []

for item in candidates:

    path = Path(item)

    entry = {
        "path": str(path),
        "status": "review_required",
        "reason": [],
        "generated": datetime.now(timezone.utc).isoformat()
    }


    if path.suffix == ".sh":
        entry["reason"].append(
            "legacy shell implementation candidate"
        )

    if "test" in path.name.lower():
        entry["reason"].append(
            "test or validation artifact"
        )

    if "old" in path.name.lower() or "bak" in path.name.lower():
        entry["reason"].append(
            "backup artifact"
        )

    if not entry["reason"]:
        entry["reason"].append(
            "not reachable from runtime entry path"
        )


    manifest.append(entry)



out = REPORT/"quarantine_manifest.json"

out.write_text(
    json.dumps(
        manifest,
        indent=2
    )
)


print("Quarantine manifest created")
print("Candidates:",len(manifest))
print("Output:",out)
