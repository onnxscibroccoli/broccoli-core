#!/usr/bin/env python3
"""Fail-closed proof of the Broccoli Android Rish transport boundary."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import secrets
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.android_transport import RishTransport

DEFAULT_OUTPUT = "/sdcard/OmniKali/broccoli/rish-transport-proof.txt"


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    output_path: str
    evidence: str
    error: str = ""


def validate_output_path(value: str) -> str:
    path = PurePosixPath(value)
    text = str(path)
    if ".." in path.parts:
        raise ValueError("probe output path may not contain '..'")
    if not (
        text.startswith("/sdcard/")
        or text.startswith("/storage/emulated/0/")
    ):
        raise ValueError("probe output must use Android shared storage")
    return text


def build_probe_command(output_path: str, marker: str) -> str:
    output_path = validate_output_path(output_path)
    parent = str(PurePosixPath(output_path).parent)
    qout = shlex.quote(output_path)
    qparent = shlex.quote(parent)
    qmarker = shlex.quote(marker)
    return (
        f"mkdir -p {qparent} && "
        f"printf '%s\\n' {qmarker} > {qout} && "
        f"id >> {qout} && "
        f"getprop ro.build.version.sdk >> {qout} && "
        f"test -s {qout} && cat {qout}"
    )


def run_probe(
    output_path: str = DEFAULT_OUTPUT,
    *,
    transport=None,
    timeout: float = 20.0,
    marker: str | None = None,
) -> ProbeResult:
    output_path = validate_output_path(output_path)
    marker = marker or f"RDC_RISH_TARGET_OK_{secrets.token_hex(8)}"
    backend = transport or RishTransport(timeout=timeout)
    try:
        result = backend.run(
            build_probe_command(output_path, marker), timeout=timeout
        )
    except Exception as exc:
        return ProbeResult(False, output_path, "", str(exc))

    evidence = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        return ProbeResult(
            False,
            output_path,
            evidence,
            f"transport rc={result.returncode}",
        )
    if marker not in evidence:
        return ProbeResult(False, output_path, evidence, "target marker missing")
    if "uid=2000(shell)" not in evidence:
        return ProbeResult(False, output_path, evidence, "Android shell identity missing")
    return ProbeResult(True, output_path, evidence)


def main(argv: list[str]) -> int:
    output = argv[1] if len(argv) > 1 else DEFAULT_OUTPUT
    try:
        result = run_probe(output)
    except ValueError as exc:
        print(f"RISH_TRANSPORT_NOT_PROVEN: {exc}", file=sys.stderr)
        return 14

    if not result.ok:
        print(
            f"RISH_TRANSPORT_NOT_PROVEN: {result.error or 'unknown failure'}",
            file=sys.stderr,
        )
        if result.evidence:
            print(result.evidence, file=sys.stderr, end="" if result.evidence.endswith("\n") else "\n")
        return 12

    print("RISH_TRANSPORT_PASS")
    print(f"artifact={result.output_path}")
    print(result.evidence, end="" if result.evidence.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
