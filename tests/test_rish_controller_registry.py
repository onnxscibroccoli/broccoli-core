import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import rish_controller_registry as rcr


def _write(obj):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(obj, f)
    f.close()
    return f.name


def _base(**over):
    d = {"schema": rcr.SCHEMA, "required_rish_uid": 2000,
         "controllers": [{"package_id": "com.termux", "rish_uid": 2000, "transport": "rish_cli"}]}
    d.update(over)
    return d


class SeedRegistry(unittest.TestCase):
    def test_seed_entries(self):
        reg = rcr.load_registry()
        self.assertEqual(set(reg), {"com.termux", "labs.magi.mobilemcp", "org.broccoli.controller"})
        self.assertTrue(all(c.rish_uid == 2000 for c in reg.values()))

    def test_authorize_each_seed(self):
        for pkg in ("com.termux", "labs.magi.mobilemcp", "org.broccoli.controller"):
            self.assertEqual(rcr.authorize(pkg, 2000).package_id, pkg)

    def test_hybrid_id_matches_gradle(self):
        g = (ROOT / "hybrid/android/app/build.gradle").read_text()
        self.assertIn("applicationId 'org.broccoli.controller'", g)


class Refusals(unittest.TestCase):
    def test_unknown_package(self):
        with self.assertRaisesRegex(rcr.ControllerRefused, "not registered"):
            rcr.authorize("com.example.evil", 2000)

    def test_missing_caller_no_termux_fallback(self):
        for bad in (None, ""):
            with self.assertRaisesRegex(rcr.ControllerRefused, "no default"):
                rcr.authorize(bad, 2000)

    def test_wrong_uid(self):
        for uid in (0, 10123, -1, "2000", 2000.0, True, None):
            with self.assertRaises(rcr.ControllerRefused):
                rcr.authorize("com.termux", uid)

    def test_case_and_prefix_not_matched(self):
        for pkg in ("COM.TERMUX", "com.termux.api", "com.termu"):
            with self.assertRaises(rcr.ControllerRefused):
                rcr.authorize(pkg, 2000)


class InvalidRegistry(unittest.TestCase):
    def assertInvalid(self, obj):
        with self.assertRaises(rcr.RegistryInvalid):
            rcr.load_registry(_write(obj))

    def test_missing_file(self):
        with self.assertRaises(rcr.RegistryInvalid):
            rcr.load_registry("/nonexistent/rish_controllers.json")

    def test_bad_json(self):
        f = _write({}); Path(f).write_text("{not json")
        with self.assertRaises(rcr.RegistryInvalid):
            rcr.load_registry(f)

    def test_schema_uid_empty(self):
        self.assertInvalid(_base(schema="other"))
        self.assertInvalid(_base(required_rish_uid=0))
        self.assertInvalid(_base(controllers=[]))

    def test_bad_entries(self):
        e = {"package_id": "com.termux", "rish_uid": 2000, "transport": "rish_cli"}
        self.assertInvalid(_base(controllers=[dict(e, rish_uid=0)]))
        self.assertInvalid(_base(controllers=[dict(e, transport="tcp_open")]))
        self.assertInvalid(_base(controllers=[dict(e, package_id="not a pkg")]))
        self.assertInvalid(_base(controllers=[e, e]))

    def test_valid_custom(self):
        self.assertIn("com.termux", rcr.load_registry(_write(_base())))


class Cli(unittest.TestCase):
    def run_cli(self, *a):
        return subprocess.run([sys.executable, str(ROOT / "tools/rish_controller_registry.py"), *a],
                              capture_output=True, text=True)

    def test_cli_allow_and_refuse(self):
        self.assertEqual(self.run_cli("labs.magi.mobilemcp", "2000").returncode, 0)
        self.assertEqual(self.run_cli("com.example.x", "2000").returncode, 3)
        self.assertEqual(self.run_cli("com.termux", "0").returncode, 3)
        self.assertEqual(self.run_cli().returncode, 3)


if __name__ == "__main__":
    unittest.main()
