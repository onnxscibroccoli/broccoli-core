"""Canonical checkout must import grok_xml_parse without ~/broccoli."""
import unittest
from pathlib import Path

import smoke_fast


class SmokeFastBoundaryTest(unittest.TestCase):
    def test_root_is_this_checkout(self):
        repo = Path(__file__).resolve().parents[1]
        self.assertEqual(smoke_fast.ROOT, repo)
        self.assertTrue((smoke_fast.ROOT / "lib" / "grok_xml_parse.py").is_file())

    def test_self_test_passes_without_a_device(self):
        self.assertEqual(smoke_fast.self_test(), 0)

    def test_cache_stamp_changes_when_parser_changes(self):
        first = smoke_fast.contract_stamp()
        self.assertEqual(len(first), 64)
        self.assertEqual(first, smoke_fast.contract_stamp())


if __name__ == "__main__":
    unittest.main()
