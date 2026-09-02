"""Unix-atomic wrapper around the official Grok Build CLI.

The CLI is already authenticated on-device (~/.grok/auth.json) and
routes through cli-chat-proxy.grok.com, which bills the SuperGrok
weekly pool. Broccoli shells out to `grok -p` instead of hitting
api.x.ai (that ledger 402s SuperGrok OAuth).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple


DEFAULT_GROK_BIN = Path.home() / ".grok" / "bin" / "grok"
DEFAULT_AUTH = Path.home() / ".grok" / "auth.json"


def grok_bin() -> Optional[Path]:
    env = os.getenv("GROK_BIN")
    if env:
        p = Path(env)
        if p.is_file() and os.access(p, os.X_OK):
            return p
    if DEFAULT_GROK_BIN.is_file() and os.access(DEFAULT_GROK_BIN, os.X_OK):
        return DEFAULT_GROK_BIN
    found = shutil.which("grok")
    return Path(found) if found else None


def cli_ready() -> bool:
    return grok_bin() is not None and DEFAULT_AUTH.is_file()


def ask(prompt: str, timeout: float = 180.0) -> Tuple[bool, str]:
    """Run `grok -p PROMPT`. Returns (ok, text_or_error)."""
    binary = grok_bin()
    if binary is None:
        return False, "grok CLI not found — install: curl -fsSL https://x.ai/cli/install.sh | bash"
    if not DEFAULT_AUTH.is_file():
        return False, "no ~/.grok/auth.json — run: grok login --device-auth"
    env = os.environ.copy()
    env["PATH"] = f"{binary.parent}{os.pathsep}{env.get('PATH', '')}"
    try:
        proc = subprocess.run(
            [str(binary), "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"grok CLI timed out after {timeout}s"
    except OSError as exc:
        return False, f"grok CLI exec failed: {exc}"
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return False, err or out or f"grok CLI exit {proc.returncode}"
    return True, out
