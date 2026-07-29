from pathlib import Path
import ast
import json
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path.cwd()

ACTIVE_ROOTS = {
    "runtime",
    "drivers",
    "lib",
    "providers"
}

IGNORE_DIRS = {
    ".git",
    "_quarantine",
    "quarantine",
    "BroccoliWorkspaceBackup",
    "reports",
    "state",
    "__pycache__",
    "tests"
}

IGNORE_IMPORTS = {
    "os","sys","json","time","pathlib",
    "typing","subprocess","logging",
    "datetime","collections","threading",
    "re","hashlib","argparse","shutil",
    "xml","abc","dataclasses",
    "unittest","importlib",
    "__future__"
}

graph = defaultdict(list)

for root in ACTIVE_ROOTS:
    base = ROOT / root
    if not base.exists():
        continue

    for path in base.rglob("*.py"):

        if any(x in path.parts for x in IGNORE_DIRS):
            continue

        try:
            tree = ast.parse(
                path.read_text(errors="ignore")
            )
        except:
            continue

        deps=[]

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for item in node.names:
                    name=item.name.split(".")[0]
                    if name not in IGNORE_IMPORTS:
                        deps.append(item.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name=node.module.split(".")[0]
                    if name not in IGNORE_IMPORTS:
                        deps.append(node.module)

        graph[str(path.relative_to(ROOT))] = sorted(set(deps))


reverse=defaultdict(list)

for src,deps in graph.items():
    for dep in deps:
        reverse[dep].append(src)


ranking=[]

for module,users in reverse.items():
    ranking.append({
        "module":module,
        "dependents":len(users),
        "examples":users[:8]
    })

ranking.sort(
    key=lambda x:x["dependents"],
    reverse=True
)

reports=ROOT/"reports"

(reports/"production_dependency_map.json").write_text(
    json.dumps({
        "generated":
        datetime.now(timezone.utc).isoformat(),
        "files":
        len(graph),
        "modules":
        len(ranking),
        "ranking":
        ranking
    },indent=2)
)

print("Production dependency map complete")
print("Files:",len(graph))
print("Modules:",len(ranking))
print("Output:")
print("reports/production_dependency_map.json")
