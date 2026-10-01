"""Static APK inspection with bounded local tooling and no arbitrary commands.

The inspector prefers platform tooling (aapt2/aapt/apkanalyzer) when present,
then falls back to a safe ZIP inventory. It never executes APK contents.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from typing import Any


def _tool_output(argv: list[str], timeout: float = 10.0) -> dict[str, Any] | None:
    tool = shutil.which(argv[0])
    if not tool:
        return None
    try:
        proc = subprocess.run(
            [tool, *argv[1:]],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return {
        "tool": os.path.basename(tool),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def inspect_apk(path: str) -> dict[str, Any]:
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    stat = os.stat(path)
    result: dict[str, Any] = {
        "schema": "omnikali.application.apk/v1",
        "path": path,
        "size_bytes": stat.st_size,
        "tools": [],
    }

    for argv in (
        ["aapt2", "dump", "badging", path],
        ["aapt", "dump", "badging", path],
        ["apkanalyzer", "manifest", "print", path],
    ):
        output = _tool_output(argv)
        if output is not None:
            result["tools"].append(output)
            if output["returncode"] == 0 and output["stdout"]:
                result["primary_tool"] = output
                break

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        result["entries"] = len(names)
        result["has_android_manifest"] = "AndroidManifest.xml" in names
        result["native_libs"] = sorted(
            name for name in names if name.startswith("lib/") and name.endswith(".so")
        )
        result["dex_files"] = sorted(
            name for name in names if name.startswith("classes") and name.endswith(".dex")
        )
        result["resource_roots"] = sorted(
            {name.split("/", 1)[0] for name in names if "/" in name}
        )[:200]
        result["layout_candidates"] = sorted(
            name for name in names
            if name.startswith("res/layout") or name.startswith("res/xml")
        )[:1000]

    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("apk")
    args = parser.parse_args()
    print(json.dumps(inspect_apk(args.apk), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
