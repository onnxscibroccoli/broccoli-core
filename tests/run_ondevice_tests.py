#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in ("tests.test_watchme", "tests.test_watch_bridge"):
        suite.addTests(loader.loadTestsFromName(name))
    try:
        import tests.test_virtual_surface as tvs

        for attr in dir(tvs):
            fn = getattr(tvs, attr)
            if attr.startswith("test_") and callable(fn):
                suite.addTest(unittest.FunctionTestCase(fn))
    except Exception as exc:
        print("virtual_surface load:", exc)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
