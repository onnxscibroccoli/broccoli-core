# SPDX-License-Identifier: MIT
"""Verify alpha and original manifests can coexist without resource collisions."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "android"))
from package_variant import ALPHA, ANDROID, BASE, write_variant


class PackageVariantTest(unittest.TestCase):
    def test_separate_package_and_provider_authorities(self):
        manifest = ROOT / "android" / "AndroidManifest.xml"
        with tempfile.TemporaryDirectory() as tmp:
            for package in (BASE, ALPHA):
                out = Path(tmp) / (package + ".xml")
                write_variant(manifest, out, package)
                root = ET.parse(out).getroot()
                self.assertEqual(root.attrib["package"], package)
                app = root.find("application")
                self.assertEqual(app.get("{" + ANDROID + "}label"),
                                 "RoofMeasure Alpha" if package == ALPHA else "@string/app_name")
                activity = app.find("activity")
                provider = app.find("provider")
                self.assertEqual(activity.get("{" + ANDROID + "}name"), BASE + ".MainActivity")
                self.assertEqual(provider.get("{" + ANDROID + "}name"), BASE + ".ReportProvider")
                self.assertEqual(provider.get("{" + ANDROID + "}authorities"), package + ".reports")

    def test_fail_closed_on_unexpected_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_variant(ROOT / "android" / "AndroidManifest.xml",
                              Path(tmp) / "bad.xml", "com.fake.other")


if __name__ == "__main__":
    unittest.main()
