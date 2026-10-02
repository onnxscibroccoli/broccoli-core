"""Unit tests for the Phase 1 evidence collector. No device, no provider."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.grok.evidence import collect, detect_context, redact
from runtime.grok.prompts import status_prompt
from runtime.grok.store import write_status


class EvidenceTests(unittest.TestCase):
    def test_context_termux_vs_rish(self) -> None:
        termux = detect_context({"HOME": "/data/data/com.termux/files/home", "TERMUX_VERSION": "0.118"})
        rish = detect_context({"HOME": "/", "BROCC_SHELL": "rish"})
        self.assertEqual(termux["name"], "termux")
        self.assertEqual(rish["name"], "rish")
        self.assertIn("not on this PATH", rish["note"])
        self.assertIn("$HOME/brocc", detect_context({"HOME": "/data/data/com.termux/files/home", "TERMUX_VERSION": "1"})["note"])

    def test_redacts_secrets(self) -> None:
        self.assertIn("<redacted>", redact("api_key=super-secret-value"))

    def test_collect_missing_artifacts_degrades(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runtime" / "governor").mkdir(parents=True)
            (root / "runtime" / "providers").mkdir(parents=True)
            envelope = collect(root, env={"HOME": "/data/data/com.termux/files/home", "TERMUX_VERSION": "1"})
            self.assertEqual(envelope["schema_version"], 1)
            self.assertFalse(envelope["authority"]["grok_may_execute"])
            self.assertEqual(envelope["execution_context"], "termux")
            self.assertFalse(envelope["sections"]["harvest"]["ok"])
            self.assertIn("Grok", status_prompt(envelope))
            path = write_status(root, envelope)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["kind"], "grok.status")


if __name__ == "__main__":
    unittest.main()
