from pathlib import Path
import ast
import json
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path.cwd()

IGNORE = {
    "os","sys","json","time","pathlib",
    "typing","subprocess","logging",
    "datetime","collections","threading",
    "re","hashlib","argparse","shutil",
    "xml","abc","dataclasses",
    "unittest","importlib"
}

graph = defaultdict(list)

for path in ROOT.rglob("*.py"):
    if ".git" in path.parts:
        continue
    if "quarantine" in path.parts:
        continue

    try:
        tree = ast.parse(
            path.read_text(errors="ignore")
        )
    except Exception:
        continue

    imports=[]

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for item in node.names:
                name=item.name

                if (
                    name.split(".")[0]
                    not in IGNORE
                ):
                    imports.append(name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                name=node.module

                if (
                    name.split(".")[0]
                    not in IGNORE
                ):
                    imports.append(name)

    graph[str(path)] = sorted(set(imports))


reports=ROOT/"reports"

(reports/"import_graph_clean.json").write_text(
    json.dumps(graph,indent=2)
)

reverse=defaultdict(list)

for src,deps in graph.items():
    for dep in deps:
        reverse[dep].append(src)

(reports/"reverse_dependencies_clean.json").write_text(
    json.dumps(reverse,indent=2)
)

ranking=[]

for module,users in reverse.items():
    ranking.append({
        "module":module,
        "dependents":len(users),
        "examples":users[:5]
    })

ranking.sort(
    key=lambda x:x["dependents"],
    reverse=True
)

(reports/"runtime_dependency_ranking.json").write_text(
    json.dumps({
        "generated":
            datetime.now(timezone.utc).isoformat(),
        "ranking":ranking
    },indent=2)
)

print("Clean dependency graph generated")
print("Modules:",len(ranking))
print("Reports:")
print(" reports/import_graph_clean.json")
print(" reports/runtime_dependency_ranking.json")
