import json
import tempfile
import unittest
import zipfile

from tools.apk_inspector import inspect_apk


class ApkInspectorTests(unittest.TestCase):
    def test_inventory_is_safe_and_structured(self):
        with tempfile.NamedTemporaryFile(suffix=".apk") as handle:
            with zipfile.ZipFile(handle.name, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"binary-placeholder")
                archive.writestr("classes.dex", b"dex")
                archive.writestr("lib/arm64-v8a/libdemo.so", b"so")
                archive.writestr("res/layout/main.xml", b"xml")
            result = inspect_apk(handle.name)

        self.assertEqual(result["schema"], "omnikali.application.apk/v1")
        self.assertTrue(result["has_android_manifest"])
        self.assertEqual(result["dex_files"], ["classes.dex"])
        self.assertEqual(result["native_libs"], ["lib/arm64-v8a/libdemo.so"])
        self.assertEqual(result["layout_candidates"], ["res/layout/main.xml"])


if __name__ == "__main__":
    unittest.main()
