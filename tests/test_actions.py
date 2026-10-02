import unittest

from tools.actions import ActionDispatcher


class FakeBackend:
    def __init__(self):
        self.calls = []

    def run(self, command):
        self.calls.append(command)
        return command


class ActionTests(unittest.TestCase):
    def test_tap(self):
        backend = FakeBackend()
        ActionDispatcher(backend).execute({"action": "tap", "display_id": 0, "x": 100, "y": 200})
        self.assertEqual(backend.calls, ["input -d 0 tap 100 200"])

    def test_swipe(self):
        backend = FakeBackend()
        ActionDispatcher(backend).execute({
            "action": "swipe", "display_id": 0,
            "start": [10, 20], "end": [100, 200], "duration_ms": 300,
        })
        self.assertEqual(backend.calls, ["input -d 0 swipe 10 20 100 200 300"])

    def test_text(self):
        backend = FakeBackend()
        ActionDispatcher(backend).execute({"action": "text", "display_id": 0, "text": "hello"})
        self.assertEqual(backend.calls, ["input -d 0 text hello"])

    def test_invalid_action(self):
        with self.assertRaises(ValueError):
            ActionDispatcher(FakeBackend()).execute({"action": "explode"})


if __name__ == "__main__":
    unittest.main()
