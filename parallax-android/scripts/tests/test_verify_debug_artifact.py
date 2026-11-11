"""Pure Python tests for Parallax debug-only APK provenance. No network/SDK."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_debug_artifact import build_manifest

SHA = "e" * 40
URL = "https://github.com/onnxscibroccoli/broccoli-core/actions/runs/123456"
CONFIG = """android {
    defaultConfig {
        applicationId = "com.parallax.entrainment.v22"
        versionName = "2.2.1"
    }
}
"""


class ArtifactVerificationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.apk = self.root / "app-debug.apk"
        with ZipFile(self.apk, "w") as z:
            z.writestr("AndroidManifest.xml", b"manifest")
            z.writestr("classes.dex", b"classes")
        self.sums = self.root / "SHA256SUMS.txt"
        self.sums.write_text(hashlib.sha256(self.apk.read_bytes()).hexdigest() +
                             "  parallax-android/app/build/outputs/apk/debug/app-debug.apk\n")
        self.gradle = self.root / "build.gradle.kts"
        self.gradle.write_text(CONFIG)

    def check(self, sha=SHA, url=URL):
        return build_manifest(self.apk, self.sums, self.gradle, sha, url)

    def test_accepted_debug_manifest(self):
        x = self.check()
        self.assertEqual(x["app_id"], "com.parallax.entrainment.v22")
        self.assertEqual(x["version"], "2.2.1")
        self.assertEqual(x["build_type"], "debug")
        self.assertEqual(x["release_status"], "NOT_A_PRODUCTION_RELEASE")
        self.assertEqual(x["sha256"], hashlib.sha256(self.apk.read_bytes()).hexdigest())

    def test_checksum_mismatch(self):
        self.sums.write_text("0" * 64 + "  app-debug.apk\n")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.check()

    def test_checksum_unrelated_filename(self):
        self.sums.write_text("0" * 64 + "  other.apk\n")
        with self.assertRaisesRegex(ValueError, "another APK"):
            self.check()

    def test_missing_signature_provenance_claims(self):
        x = self.check()
        self.assertIn("production signing", x["unverified"])
        self.assertIn("medical or therapeutic effect", x["unverified"])

    def test_reject_different_package(self):
        self.gradle.write_text(CONFIG.replace("com.parallax.entrainment.v22", "com.parallax.entrainment"))
        with self.assertRaisesRegex(ValueError, "unexpected v2.2 Android package"):
            self.check()

    def test_reject_short_sha_and_wrong_run_url(self):
        with self.assertRaisesRegex(ValueError, "full 40-character"):
            self.check(sha="main")
        with self.assertRaisesRegex(ValueError, "first-party GitHub Actions"):
            self.check(url="https://example.net/123")

    def test_invalid_zip_and_missing_dex(self):
        self.apk.write_bytes(b"broken")
        with self.assertRaises(Exception):
            self.check()
        with ZipFile(self.apk, "w") as z:
            z.writestr("AndroidManifest.xml", b"manifest")
        with self.assertRaisesRegex(ValueError, "classes.dex"):
            self.check()


if __name__ == "__main__":
    unittest.main()
