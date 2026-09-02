from runtime.providers import grok_cli


def test_grok_bin_handles_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("GROK_BIN", raising=False)
    monkeypatch.setattr(grok_cli, "DEFAULT_GROK_BIN", tmp_path / "missing")
    monkeypatch.setattr(grok_cli.shutil, "which", lambda _name: None)
    assert grok_cli.grok_bin() is None
    assert grok_cli.cli_ready() is False


def test_ask_reports_missing_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(grok_cli, "grok_bin", lambda: None)
    ok, text = grok_cli.ask("hi")
    assert ok is False
    assert "not found" in text
