"""Broccoli Core runtime package.

Makes `import runtime.X` and `python -m runtime.X` work from any cwd.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
