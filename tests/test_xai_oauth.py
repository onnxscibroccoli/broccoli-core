"""Offline tests for the xAI OAuth token helpers."""
from __future__ import annotations

import json
import time
from pathlib import Path

from runtime.providers.xai_oauth import (
    TokenSet,
    clear_tokens,
    load_tokens,
    save_tokens,
    main as oauth_main,
)


def test_token_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    tokens = TokenSet(
        access_token="tok-abc",
        refresh_token="ref-xyz",
        expires_at=time.time() + 3600,
        scope="api:access",
    )
    save_tokens(tokens, path)
    loaded = load_tokens(path)
    assert loaded is not None
    assert loaded.access_token == "tok-abc"
    assert loaded.refresh_token == "ref-xyz"
    assert loaded.expired is False
    data = json.loads(path.read_text())
    assert data["access_token"] == "tok-abc"
    clear_tokens(path)
    assert load_tokens(path) is None


def test_cli_status_without_tokens(tmp_path: Path) -> int:
    missing = tmp_path / "nope.json"
    rc = oauth_main(["--path", str(missing), "status"])
    assert rc == 1
    return rc
