import os
import tempfile
import unittest
from pathlib import Path

try:
    from runtime.memory_vector import EncryptedMemory
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False


@unittest.skipUnless(HAS_CRYPTO, "cryptography not installed")
class TestMemory(unittest.TestCase):
    def test_remember_and_search(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mem.enc"
            m = EncryptedMemory(p)
            m.remember("turn on bluetooth", kind="intent", source="broccoli")
            m.remember("schedule dentist", kind="intent", source="broccoli")
            hits = m.search("bluetooth")
            self.assertTrue(hits)
            self.assertIn("bluetooth", hits[0].text)

    def test_file_mode(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mem.enc"
            m = EncryptedMemory(p)
            m.remember("x")
            mode = oct(p.stat().st_mode & 0o777)
            self.assertEqual(mode, "0o600")


if __name__ == "__main__":
    unittest.main()
