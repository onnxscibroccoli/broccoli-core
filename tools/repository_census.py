#!/usr/bin/env python3

import os
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path.cwd()

inventory = []
duplicates = defaultdict(list)
imports = defaultdict(list)

SKIP = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv"
}

for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP]

    for f in files:
        p = Path(root) / f
        rel = str(p.relative_to(ROOT))

        try:
            size = p.stat().st_size
        except Exception:
            size = -1

        h = None
        if p.suffix in (".py", ".sh"):
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except Exception:
                pass

        inventory.append({
            "path": rel,
            "size": size,
            "suffix": p.suffix,
            "sha256": h
        })

        duplicates[p.name].append(rel)

        if p.suffix == ".py":
            try:
                for line in p.read_text(errors="ignore").splitlines():
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        imports[rel].append(line)
            except Exception:
                pass

report = {
    "generated": datetime.utcnow().isoformat() + "Z",
    "files": len(inventory),
    "inventory": inventory,
    "duplicates": {
        k: v for k, v in duplicates.items()
        if len(v) > 1
    },
    "imports": imports
}

Path("reports/repository_inventory.json").write_text(
    json.dumps(report, indent=2)
)

with open("reports/repository_summary.md", "w") as f:
    f.write("# Repository Census\n\n")
    f.write(f"Files: {len(inventory)}\n\n")
    f.write(f"Duplicate filenames: {len(report['duplicates'])}\n\n")

    for name, paths in sorted(report["duplicates"].items()):
        f.write(f"## {name}\n")
        for p in paths:
            f.write(f"- {p}\n")
        f.write("\n")

print()
print("Repository census complete.")
print("Inventory : reports/repository_inventory.json")
print("Summary   : reports/repository_summary.md")
print("Files     :", len(inventory))
print("Duplicates:", len(report["duplicates"]))
