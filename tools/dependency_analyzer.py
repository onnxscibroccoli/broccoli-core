#!/usr/bin/env python3

import ast
import json
import os
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path.cwd()

python_files = []
imports = defaultdict(list)
reverse_imports = defaultdict(list)
executables = []
shell_scripts = []

SKIP = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache"
}

for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP]

    for name in files:
        path = Path(root) / name

        if path.suffix == ".py":
            python_files.append(path)

            try:
                tree = ast.parse(path.read_text(errors="ignore"))

                for node in ast.walk(tree):

                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports[str(path)].append(alias.name)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports[str(path)].append(node.module)

            except Exception:
                pass

        if path.suffix == ".sh":
            shell_scripts.append(str(path))

        try:
            if os.access(path, os.X_OK):
                executables.append(str(path))
        except Exception:
            pass


# Build reverse dependency map

for source, deps in imports.items():
    for dep in deps:
        reverse_imports[dep].append(source)


# Find likely entry points

entry_points = []

for path in python_files:
    try:
        text = path.read_text(errors="ignore")

        if "if __name__ == '__main__'" in text:
            entry_points.append(str(path))

        if "def main(" in text:
            entry_points.append(str(path))

    except Exception:
        pass


report = {
    "generated": datetime.now(timezone.utc).isoformat(),

    "summary": {
        "python_files": len(python_files),
        "shell_scripts": len(shell_scripts),
        "executables": len(executables),
        "entry_points": len(entry_points)
    },

    "entry_points": sorted(set(entry_points)),

    "shell_scripts": sorted(shell_scripts),

    "executables": sorted(executables),

    "imports": {
        k: v for k, v in imports.items()
    },

    "reverse_dependencies": {
        k: v for k, v in reverse_imports.items()
    }
}


Path("reports/dependency_analysis.json").write_text(
    json.dumps(report, indent=2)
)


with open("reports/dependency_analysis.md", "w") as f:

    f.write("# Dependency & Usage Analysis\n\n")

    f.write(
        json.dumps(
            report["summary"],
            indent=2
        )
    )

    f.write("\n\n## Entry Points\n\n")

    for x in report["entry_points"]:
        f.write(f"- {x}\n")

    f.write("\n\n## Shell Runtime Candidates\n\n")

    for x in report["shell_scripts"]:
        f.write(f"- {x}\n")


print("Dependency analysis complete.")
print("Python files :", len(python_files))
print("Shell files  :", len(shell_scripts))
print("Executables  :", len(executables))
print("Entry points :", len(entry_points))
print()
print("Reports:")
print(" reports/dependency_analysis.json")
print(" reports/dependency_analysis.md")
