"""Regression: CI failed because PublicBackend annotated health() as Dict without importing it."""
import unittest


class PublicBackendTypingTest(unittest.TestCase):
    def test_public_backend_imports(self):
        from runtime.drivers.accessibility.public_backend import PublicBackend

        backend = PublicBackend()
        self.assertEqual(backend.health()["backend"], "public")
        self.assertIn("supports_hidden_api", backend.capabilities())

    def test_hidden_backend_imports(self):
        from runtime.drivers.accessibility.hidden_backend import HiddenBackend

        backend = HiddenBackend()
        self.assertEqual(backend.health()["backend"], "hidden")


if __name__ == "__main__":
    unittest.main()
