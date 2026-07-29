from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path.cwd()

reports = ROOT / "reports"

graphs = json.loads(
    (reports / "import_graph.json").read_text()
)

reachable = json.loads(
    (reports / "runtime_reachable_modules.json").read_text()
)

centrality = defaultdict(int)

for src, deps in graphs.items():
    for dep in deps:
        centrality[dep] += 1

reachable_files = set()

if isinstance(reachable, dict):
    for key in [
        "reachable",
        "modules",
        "files"
    ]:
        if key in reachable:
            reachable_files.update(reachable[key])

ranking = []

for path, score in centrality.items():
    ranking.append({
        "file": path,
        "imports": score,
        "runtime_reachable":
            path in reachable_files
    })

ranking.sort(
    key=lambda x: (
        x["runtime_reachable"],
        x["imports"]
    ),
    reverse=True
)

output = {
    "generated":
        datetime.now(timezone.utc).isoformat(),
    "top_runtime_dependencies":
        ranking[:200],
    "reachable_count":
        len(reachable_files),
    "total_indexed":
        len(graphs)
}

(reports / "canonical_runtime_candidates.json").write_text(
    json.dumps(output, indent=2)
)

with open(
    reports / "canonical_runtime_candidates.md",
    "w"
) as f:
    f.write("# Canonical Runtime Candidates\n\n")
    for item in ranking[:100]:
        f.write(
            f"- {item['file']} "
            f"| imports={item['imports']} "
            f"| reachable={item['runtime_reachable']}\n"
        )

print("Canonical runtime analysis complete")
print("Candidates:", len(ranking))
print("Reports:")
print(" reports/canonical_runtime_candidates.json")
print(" reports/canonical_runtime_candidates.md")
