#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(".")
REPORT = Path("reports")

deps = defaultdict(set)

for py in ROOT.rglob("*.py"):
    if "quarantine" in str(py):
        continue

    try:
        text = py.read_text(errors="ignore")
    except:
        continue

    for line in text.splitlines():
        line=line.strip()

        if line.startswith("import "):
            mod=line.replace("import ","").split(".")[0]
            deps[str(py)].add(mod)

        elif line.startswith("from "):
            mod=line.split()[1].split(".")[0]
            deps[str(py)].add(mod)


graph={
    k:sorted(v)
    for k,v in deps.items()
}


REPORT.mkdir(exist_ok=True)

with open(REPORT/"import_graph.json","w") as f:
    json.dump(graph,f,indent=2)


reverse=defaultdict(list)

for src,mods in graph.items():
    for m in mods:
        reverse[m].append(src)


with open(REPORT/"reverse_dependencies.json","w") as f:
    json.dump(
        {k:v for k,v in reverse.items()},
        f,
        indent=2
    )


print("Dependency graph generated")
print("Files analyzed:",len(graph))
print("Reports:")
print(" reports/import_graph.json")
print(" reports/reverse_dependencies.json")
