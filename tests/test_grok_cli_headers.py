"""Offline tests for Grok CLI proxy header helpers."""
from runtime.providers import grok_cli


def test_proxy_headers_carry_cli_identity():
    h = grok_cli.proxy_headers("tok-123")
    assert h["Authorization"] == "Bearer tok-123"
    assert h["X-XAI-Token-Auth"] == "xai-grok-cli"
    assert h["x-grok-client-identifier"] == "grok-shell"
    assert h["x-grok-client-version"] == "1.0.13"
    assert h["x-authenticateresponse"] == "authenticate-response"
    assert "cli-chat-proxy" not in h  # base url is separate


def test_proxy_headers_no_api_ledger_leak():
    h = grok_cli.proxy_headers("tok")
    # Must NOT advertise the metered developer surface.
    assert "api.x.ai" not in str(h).lower()
