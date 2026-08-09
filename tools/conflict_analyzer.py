#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict
import hashlib
import json
import ast

ROOT = Path(".")
REPORT = Path("reports")
REPORT.mkdir(exist_ok=True)


hash_groups = defaultdict(list)
name_groups = defaultdict(list)
symbols = defaultdict(list)


for py in ROOT.rglob("*.py"):

    if "quarantine" in str(py):
        continue

    try:
        data = py.read_bytes()

    except:
        continue


    digest = hashlib.sha256(data).hexdigest()

    hash_groups[digest].append(str(py))
    name_groups[py.name].append(str(py))


    try:
        tree = ast.parse(
            data.decode(errors="ignore")
        )

        for node in ast.walk(tree):

            if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
                symbols[node.name].append(str(py))

    except:
        pass



duplicates = {
    k:v for k,v in hash_groups.items()
    if len(v)>1
}


filename_conflicts = {
    k:v for k,v in name_groups.items()
    if len(v)>1
}


symbol_conflicts = {
    k:v for k,v in symbols.items()
    if len(v)>1
}


with open(
    REPORT/"duplicate_clusters.json",
    "w"
) as f:
    json.dump(
        duplicates,
        f,
        indent=2
    )


with open(
    REPORT/"symbol_conflicts.json",
    "w"
) as f:
    json.dump(
        symbol_conflicts,
        f,
        indent=2
    )


with open(
    REPORT/"conflict_report.md",
    "w"
) as f:

    f.write("# Broccoli Conflict Analysis\n\n")

    f.write(
        f"## Exact duplicate files: {len(duplicates)}\n\n"
    )

    f.write(
        f"## Filename conflicts: {len(filename_conflicts)}\n\n"
    )

    f.write(
        f"## Symbol conflicts: {len(symbol_conflicts)}\n\n"
    )


print("Conflict analysis complete")
print("Duplicate groups:",len(duplicates))
print("Filename conflicts:",len(filename_conflicts))
print("Symbol conflicts:",len(symbol_conflicts))
print()
print("Reports:")
print(" reports/duplicate_clusters.json")
print(" reports/symbol_conflicts.json")
print(" reports/conflict_report.md")
