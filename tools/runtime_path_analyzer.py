#!/usr/bin/env python3

import ast
import json
from pathlib import Path
from collections import defaultdict, deque

ROOT = Path(".")
REPORT = Path("reports")

ENTRYPOINTS = [
    Path("runtime/main.py"),
    Path("runtime/start.sh"),
]

MODULE_MAP = {}

for py in ROOT.rglob("*.py"):
    if "quarantine" in str(py):
        continue

    rel = py.relative_to(ROOT)

    module = ".".join(rel.with_suffix("").parts)

    MODULE_MAP[module] = py


graph = defaultdict(set)


for module, path in MODULE_MAP.items():

    try:
        tree = ast.parse(
            path.read_text(errors="ignore")
        )

    except Exception:
        continue


    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                graph[module].add(alias.name)


        elif isinstance(node, ast.ImportFrom):

            if node.module:
                graph[module].add(node.module)



reachable=set()

queue=deque()


for ep in ENTRYPOINTS:

    if ep.exists():

        mod=".".join(
            ep.with_suffix("").parts
        )

        queue.append(mod)



while queue:

    current=queue.popleft()

    if current in reachable:
        continue

    reachable.add(current)

    for dep in graph.get(current, []):

        matches=[
            m for m in MODULE_MAP
            if m==dep or m.startswith(dep+".")
        ]

        for m in matches:
            queue.append(m)



unused=[]

for module,path in MODULE_MAP.items():

    if module not in reachable:
        unused.append(str(path))



REPORT.mkdir(exist_ok=True)


with open(
    REPORT/"runtime_reachable_modules.json",
    "w"
) as f:
    json.dump(
        sorted(reachable),
        f,
        indent=2
    )


with open(
    REPORT/"quarantine_candidates.json",
    "w"
) as f:
    json.dump(
        sorted(unused),
        f,
        indent=2
    )


print("Runtime analysis complete")
print("Reachable modules:",len(reachable))
print("Candidates:",len(unused))
print()
print("Reports:")
print(" reports/runtime_reachable_modules.json")
print(" reports/quarantine_candidates.json")
