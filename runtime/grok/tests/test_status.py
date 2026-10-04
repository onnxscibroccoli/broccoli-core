from __future__ import annotations

import json
from pathlib import Path

from runtime.grok.evidence import collect_evidence
from runtime.grok.prompts import render_prompt
from runtime.grok.store import write_status


def test_collect_degrades_without_android(tmp_path: Path) -> None:
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "prod.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "bin").mkdir()
    envelope = collect_evidence(tmp_path)
    assert envelope["schema"] == "broccoli.grok.evidence.v1"
    assert envelope["authority"]["grok_may_execute"] is False
    names = [s["name"] for s in envelope["sections"]]
    assert "git" in names
    assert "accessibility" in names
    text = render_prompt(envelope)
    assert "BROCCOLI EVIDENCE PACKET" in text
    assert "Do not expect" in text or "Termux" in text
    path = write_status(tmp_path, envelope)
    assert path.is_file()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["correlation_id"] == envelope["correlation_id"]


def test_rish_note(monkeypatch) -> None:
    monkeypatch.setenv("HOME", "/")
    monkeypatch.delenv("PREFIX", raising=False)
    monkeypatch.setenv("PATH", "/system/bin")
    from runtime.grok.evidence import execution_context

    ctx = execution_context()
    assert ctx["rish_like"] is True
    assert "Termux" in ctx["note"]
