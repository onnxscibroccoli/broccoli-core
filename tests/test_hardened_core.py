import importlib
import unittest


class HardenedCoreSmokeTest(unittest.TestCase):
    """Basic integrity checks for the hardened runtime surface."""

    REQUIRED_MODULES = (
        "runtime.bootstrap",
        "runtime.main",
        "runtime.governor.engine",
        "runtime.drivers.accessibility.driver",
        "runtime.providers.manager",
        "runtime.plugin_loader",
    )

    def test_required_runtime_modules_import(self):
        failures = []

        for name in self.REQUIRED_MODULES:
            try:
                importlib.import_module(name)
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")

        self.assertFalse(
            failures,
            "Required runtime imports failed:\n" + "\n".join(failures),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
