"""Bounded transport from the local Broccoli process to Android shell via Rish.

The transport deliberately owns only the bridge. Policy and action allowlisting
belong above it in ActionDispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import shlex

from tools.termux_run_command import available as termux_bridge_available
from tools.termux_run_command import run as termux_bridge_run


@dataclass(frozen=True)
class TransportResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def combined_output(self) -> str:
        return self.stdout + self.stderr


class RishTransport:
    """Invoke the canonical repository-local Rish wrapper."""

    def __init__(self, wrapper: str | None = None, timeout: float = 30.0):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.wrapper = wrapper or os.path.join(root, "lib", "rish_run.sh")
        self.timeout = float(timeout)

    def run(self, command: str, *, timeout: float | None = None) -> TransportResult:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("command must be a non-empty string")
        # An interactive Termux process has Android runtime variables such as
        # BOOTCLASSPATH. RDC/background child processes do not. Do not invoke
        # Rish from the reduced environment because that can hang after a
        # mutation has already happened and must never be blindly retried.
        if not os.environ.get("BOOTCLASSPATH") and termux_bridge_available():
            rc, stdout, stderr = termux_bridge_run(
                f"RISH_PRESERVE_ENV=0 bash {shlex.quote(self.wrapper)} {shlex.quote(command)}",
                timeout=self.timeout if timeout is None else float(timeout),
            )
            return TransportResult(rc, stdout, stderr)

        proc = subprocess.run(
            ["bash", self.wrapper, command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=self.timeout if timeout is None else float(timeout),
            text=True,
        )
        return TransportResult(proc.returncode, proc.stdout, proc.stderr)
