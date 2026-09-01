"""XaiOAuthProvider — device-code OAuth for SuperGrok / X Premium+.

Uses the same flow as OpenClaw, pi/piex, Newroz, and the official Grok CLI.
No XAI_API_KEY required. Tokens count against the subscription pool.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Public constants (reverse-engineered from working third-party clients)
XAI_OAUTH_ISSUER = "https://auth.x.ai"
XAI_OAUTH_DISCOVERY = f"{XAI_OAUTH_ISSUER}/.well-known/openid-configuration"
XAI_OAUTH_DEVICE_CODE_URL = f"{XAI_OAUTH_ISSUER}/oauth2/device/code"
XAI_OAUTH_TOKEN_URL = f"{XAI_OAUTH_ISSUER}/oauth2/token"
XAI_OAUTH_CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
XAI_OAUTH_SCOPE = "openid profile email offline_access grok-cli:access api:access"

# Skew so short-lived tokens don't look expired mid-request
ACCESS_TOKEN_SKEW_MS = 5 * 60 * 1000
MIN_ACCESS_TOKEN_TTL_MS = 30_000

TOKEN_STORE = Path.home() / ".broccoli" / "xai_oauth_tokens.json"


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: float = 0.0  # epoch seconds
    token_type: str = "Bearer"

    def is_expired(self) -> bool:
        return time.time() * 1000 >= (self.expires_at - ACCESS_TOKEN_SKEW_MS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OAuthTokens":
        return cls(
            access_token=d["access_token"],
            refresh_token=d.get("refresh_token"),
            expires_at=float(d.get("expires_at", 0)),
            token_type=d.get("token_type", "Bearer"),
        )


class XaiOAuthProvider:
    """OAuth-first provider. Falls back to API key only with explicit consent."""

    name = "xai-oauth"
    base_url = "https://api.x.ai/v1"

    def __init__(self, token_store: Path = TOKEN_STORE) -> None:
        self.token_store = token_store
        self._tokens: Optional[OAuthTokens] = self._load()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def has_session(self) -> bool:
        return self._tokens is not None and not self._tokens.is_expired()

    def login(self, device: bool = False) -> OAuthTokens:
        """Start device-code flow. Opens browser (or prints URL+code)."""
        device_resp = self._post_form(
            XAI_OAUTH_DEVICE_CODE_URL,
            {
                "client_id": XAI_OAUTH_CLIENT_ID,
                "scope": XAI_OAUTH_SCOPE,
            },
        )
        device_code = device_resp["device_code"]
        user_code = device_resp["user_code"]
        verification_uri = device_resp.get(
            "verification_uri_complete"
        ) or device_resp["verification_uri"]
        interval = device_resp.get("interval", 5)
        expires_in = device_resp.get("expires_in", 600)

        if device:
            print(f"Open: {verification_uri}")
            print(f"Code: {user_code}")
        else:
            try:
                import webbrowser

                webbrowser.open(verification_uri)
            except Exception:
                print(f"Open: {verification_uri}")
                print(f"Code: {user_code}")

        deadline = time.time() + expires_in
        while time.time() < deadline:
            time.sleep(interval)
            try:
                token_resp = self._post_form(
                    XAI_OAUTH_TOKEN_URL,
                    {
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        "device_code": device_code,
                        "client_id": XAI_OAUTH_CLIENT_ID,
                    },
                )
            except urllib.error.HTTPError as e:
                body = e.read().decode()
                if "authorization_pending" in body or "slow_down" in body:
                    continue
                raise
            tokens = OAuthTokens(
                access_token=token_resp["access_token"],
                refresh_token=token_resp.get("refresh_token"),
                expires_at=time.time() * 1000
                + token_resp.get("expires_in", 3600) * 1000,
                token_type=token_resp.get("token_type", "Bearer"),
            )
            self._save(tokens)
            self._tokens = tokens
            return tokens
        raise TimeoutError("Device code flow timed out")

    def logout(self) -> None:
        if self.token_store.exists():
            self.token_store.unlink()
        self._tokens = None

    def get_access_token(self) -> str:
        if self._tokens is None or self._tokens.is_expired():
            if self._tokens and self._tokens.refresh_token:
                self._refresh()
            else:
                raise RuntimeError(
                    "No active OAuth session. Run `broccoli xai login` first."
                )
        assert self._tokens is not None
        return self._tokens.access_token

    def chat(self, messages: list[dict[str, str]], model: str = "grok-4.6", **kw: Any) -> dict[str, Any]:
        """Hit the real API with the OAuth bearer. No credits charged."""
        token = self.get_access_token()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kw.get("temperature", 0),
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _refresh(self) -> None:
        assert self._tokens and self._tokens.refresh_token
        resp = self._post_form(
            XAI_OAUTH_TOKEN_URL,
            {
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.refresh_token,
                "client_id": XAI_OAUTH_CLIENT_ID,
            },
        )
        self._tokens = OAuthTokens(
            access_token=resp["access_token"],
            refresh_token=resp.get("refresh_token", self._tokens.refresh_token),
            expires_at=time.time() * 1000 + resp.get("expires_in", 3600) * 1000,
            token_type=resp.get("token_type", "Bearer"),
        )
        self._save(self._tokens)

    def _load(self) -> Optional[OAuthTokens]:
        if not self.token_store.exists():
            return None
        try:
            return OAuthTokens.from_dict(json.loads(self.token_store.read_text()))
        except Exception:
            return None

    def _save(self, tokens: OAuthTokens) -> None:
        self.token_store.parent.mkdir(parents=True, exist_ok=True)
        self.token_store.write_text(json.dumps(tokens.to_dict(), indent=2))
        try:
            os.chmod(self.token_store, 0o600)
        except Exception:
            pass

    @staticmethod
    def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())


# CLI entry (broccoli xai login / logout / status)
if __name__ == "__main__":
    import sys

    p = XaiOAuthProvider()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "login":
        p.login(device="--device" in sys.argv)
        print("Logged in. Session stored at", p.token_store)
    elif cmd == "logout":
        p.logout()
        print("Logged out.")
    elif cmd == "status":
        print("Has session:", p.has_session())
    else:
        print("Usage: xai_oauth.py [login|logout|status] [--device]")
