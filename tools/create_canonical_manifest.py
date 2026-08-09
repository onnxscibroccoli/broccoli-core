from pathlib import Path
import json
from datetime import datetime, timezone

manifest = {
    "generated":
        datetime.now(timezone.utc).isoformat(),

    "production_roots": [
        "runtime",
        "drivers",
        "lib"
    ],

    "canonical_runtime": [
        "runtime/main.py",
        "runtime/eventbus",
        "runtime/governor",
        "runtime/planner",
        "runtime/workflow",
        "runtime/providers",
        "drivers/accessibility"
    ],

    "migration_targets": [
        "lib/broccoli_rish_shell.py",
        "lib/broccoli_ui_dump.py",
        "lib/broccoli_input.py",
        "lib/broccoli_strategy.py",
        "task_queue.py",
        "event_bus.py"
    ],

    "quarantine_policy": {
        "delete": False,
        "preserve_history": True,
        "move_only_after_dependency_review": True
    }
}

Path(
    "reports/canonical_manifest.json"
).write_text(
    json.dumps(manifest, indent=2)
)

print("Canonical manifest created")
print("reports/canonical_manifest.json")
