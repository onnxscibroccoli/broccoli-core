import unittest

from tools.actions import ActionDispatcher


class FakeBackend:
    def __init__(self):
        self.calls = []

    def run(self, command):
        self.calls.append(command)
        return command


class AndroidActionContractTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.dispatcher = ActionDispatcher(self.backend)

    def test_identity_is_allowlisted(self):
        self.dispatcher.execute({"action": "device.identity"})
        self.assertIn("OMNIKALI_ANDROID_IDENTITY_OK", self.backend.calls[0])

    def test_ui_dump_is_allowlisted(self):
        self.dispatcher.execute({"action": "ui.dump"})
        self.assertIn("uiautomator dump", self.backend.calls[0])

    def test_package_name_is_bounded(self):
        self.dispatcher.execute({"action": "package.inspect", "package": "com.example.app"})
        self.assertIn("pm path com.example.app", self.backend.calls[0])

    def test_package_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            self.dispatcher.execute({"action": "package.inspect", "package": "com.example;id"})

    def test_export_is_allowlisted(self):
        self.dispatcher.execute({"action": "package.export", "package": "com.example.app"})
        self.assertIn("OMNIKALI_PACKAGE_EXPORT_OK", self.backend.calls[0])

    def test_launch_is_allowlisted(self):
        self.dispatcher.execute({"action": "app.launch", "package": "com.example.app"})
        self.assertIn("monkey -p com.example.app", self.backend.calls[0])

    def test_stop_requires_confirmation(self):
        with self.assertRaises(ValueError):
            self.dispatcher.execute({"action": "app.stop", "package": "com.example.app"})

    def test_display_list_is_allowlisted(self):
        self.dispatcher.execute({"action": "display.list"})
        self.assertTrue(self.backend.calls[0].startswith("dumpsys display"))

    def test_tap_is_bounded(self):
        self.dispatcher.execute({"action": "tap", "display_id": 0, "x": 10, "y": 20})
        self.assertEqual(self.backend.calls[0], "input -d 0 tap 10 20")

    def test_swipe_rejects_excessive_duration(self):
        with self.assertRaises(ValueError):
            self.dispatcher.execute({
                "action": "swipe", "display_id": 0,
                "start": [0, 0], "end": [1, 1], "duration_ms": 120001,
            })

    def test_text_quotes_shell_input(self):
        self.dispatcher.execute({"action": "text", "display_id": 0, "text": "hello 'world'"})
        self.assertIn("input -d 0 text", self.backend.calls[0])

    def test_keyevent_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            self.dispatcher.execute({"action": "keyevent", "display_id": 0, "key": "HOME;id"})

    def test_unknown_action_fails_closed(self):
        with self.assertRaises(ValueError):
            self.dispatcher.execute({"action": "shell", "command": "id"})


if __name__ == "__main__":
    unittest.main()
