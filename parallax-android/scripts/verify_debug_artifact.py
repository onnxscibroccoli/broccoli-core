#!/usr/bin/env python3
"""Fail-closed provenance manifest for a debug-only Parallax Distortion v2.2 APK.

No network, signing secrets, production release, or telemetry.
This verifies APK archive/checksum metadata; Android signature verification is
separately enforced in the GitHub Actions workflow with apksigner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import BadZipFile, ZipFile

SHA_40 = re.compile(r"^[0-9a-fA-F]{40}$")
SHA_256 = re.compile(r"^[0-9a-fA-F]{64}$")
RUN_URL = re.compile(r"^https://github\.com/onnxscibroccoli/broccoli-core/actions/runs/[1-9]\d*$")


def kotlin_config(text: str, field: str) -> str:
    m = re.search(r"^\s*" + re.escape(field) + r"\s*=\s*\"([^\"]+)\"\s*$", text, re.M)
    if not m:
        raise ValueError("missing Gradle config: " + field)
    return m.group(1)


def build_manifest(apk: Path, sums: Path, build_script: Path,
                   source_sha: str, run_url: str) -> dict:
    if not SHA_40.fullmatch(source_sha):
        raise ValueError("expected full 40-character source checkout SHA")
    if not RUN_URL.fullmatch(run_url):
        raise ValueError("expected exact first-party GitHub Actions run URL")
    if apk.name != "app-debug.apk" or not apk.is_file() or apk.stat().st_size <= 0:
        raise ValueError("debug APK is missing or invalid")
    with ZipFile(apk) as archive:
        files = set(archive.namelist())
        if "AndroidManifest.xml" not in files or "classes.dex" not in files:
            raise ValueError("APK missing AndroidManifest.xml or classes.dex")
        corrupt = archive.testzip()
        if corrupt is not None:
            raise ValueError("APK zip CRC failed on " + corrupt)
    with apk.open("rb") as fh:
        calculated = hashlib.file_digest(fh, "sha256").hexdigest()
    rows = sums.read_text(encoding="utf-8").strip().splitlines()
    if len(rows) != 1:
        raise ValueError("expected exactly one recorded sha256sum")
    parts = rows[0].split(maxsplit=1)
    if len(parts) != 2 or not SHA_256.fullmatch(parts[0]):
        raise ValueError("invalid sha256sum record")
    if Path(parts[1].lstrip("*")).name != apk.name:
        raise ValueError("sha256sum belongs to another APK")
    if parts[0].lower() != calculated:
        raise ValueError("independent digest mismatch")
    gradle = build_script.read_text(encoding="utf-8")
    appid = kotlin_config(gradle, "applicationId")
    version = kotlin_config(gradle, "versionName")
    if appid != "com.parallax.entrainment.v22":
        raise ValueError("unexpected v2.2 Android package ID")
    return {
        "schema_version": 1,
        "build_type": "debug",
        "evidence": "CI_EXECUTED_BUILD_ONLY",
        "release_status": "NOT_A_PRODUCTION_RELEASE",
        "app_id": appid,
        "version": version,
        "file": apk.name,
        "bytes": apk.stat().st_size,
        "sha256": calculated,
        "source_checkout_sha": source_sha,
        "workflow_run": run_url,
        "required_build_gates": ["testDebugUnitTest", "lintDebug", "assembleDebug", "apksigner verify"],
        "unverified": [
            "physical device installation",
            "ultrasonic hardware fidelity and spatial positioning",
            "microphone-to-audio spectral accuracy on target device",
            "production signing",
            "medical or therapeutic effect",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--sums", required=True, type=Path)
    parser.add_argument("--build-script", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    obj = build_manifest(args.apk, args.sums, args.build_script, args.source_sha, args.run_url)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PARALLAX_DEBUG_VERIFIED: " + obj["sha256"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, BadZipFile) as exc:
        print("PARALLAX_DEBUG_INVALID: " + str(exc), file=sys.stderr)
        sys.exit(1)
