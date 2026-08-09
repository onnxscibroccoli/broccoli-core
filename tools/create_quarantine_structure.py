from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

ROOT = Path.cwd()

manifest = ROOT / "reports/quarantine_manifest.json"

qroot = ROOT / "quarantine"

for d in [
    "python",
    "shell",
    "duplicates",
    "conflicts",
    "snapshots",
]:
    (qroot / d).mkdir(parents=True, exist_ok=True)

metadata = {
    "created": datetime.now(timezone.utc).isoformat(),
    "purpose": "Broccoli Core development quarantine archive",
    "policy": {
        "delete": False,
        "preserve_history": True,
        "restore_possible": True
    }
}

(qroot / "quarantine_metadata.json").write_text(
    json.dumps(metadata, indent=2)
)

print("Quarantine structure ready")
print(qroot)
