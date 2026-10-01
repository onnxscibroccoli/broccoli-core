"""Bounded transport from the local Broccoli process to Android shell via Rish.

The transport deliberately owns only the bridge. Policy and action allowlisting
belong above it in ActionDispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class TransportResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class RishTransport:
    """Invoke the canonical repository-local Rish wrapper."""

    def __init__(self, wrapper: str | None = None, timeout: float = 30.0):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.wrapper = wrapper or os.path.join(root, "lib", "rish_run.sh")
        self.timeout = float(timeout)

    def run(self, command: str, *, timeout: float | None = None) -> TransportResult:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("command must be a non-empty string")
        proc = subprocess.run(
            ["bash", self.wrapper, command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=self.timeout if timeout is None else float(timeout),
            text=True,
        )
        return TransportResult(proc.returncode, proc.stdout, proc.stderr)
