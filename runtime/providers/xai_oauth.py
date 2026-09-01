"""xAI OAuth device-code provider + CLI.

This is a single module on purpose. Do not also ship a
`runtime/providers/xai_oauth/` package — Python cannot resolve both
`xai_oauth.py` and `xai_oauth/` in the same directory, which is what
broke `python -m runtime.providers.xai_oauth login` on Termux.

Usage from the repo root:
    python -m runtime.providers.xai_oauth login
    python -m runtime.providers.xai_oauth status
    python -m runtime.providers.xai_oauth logout

Or from anywhere (Termux-friendly):
    python runtime/providers/xai_oauth.py login
    bin/xai-oauth login
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional


def _ensure_repo_on_path() -> None:
    """Allow `python runtime/providers/xai_oauth.py login` from any cwd."""
    here = Path(__file__).resolve()
    # .../broccoli-core/runtime/providers/xai_oauth.py -> repo root
    root = here.parents[2]
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)


_ensure_repo_on_path()

ISSUER = "https://auth.x.ai"
DISCOVERY_URL = f"{ISSUER}/.well-known/openid-configuration"
DEVICE_CODE_URL = f"{ISSUER}/oauth2/device/code"

CLIENT_ID = os.getenv(
    "XAI_OAUTH_CLIENT_ID",
    "b1a00492-073a-47ea-816f-4c329264a828",
)
SCOPE = os.getenv(
    "XAI_OAUTH_SCOPE",
    "openid profile email offline_access grok-cli:access api:access",
)

DEFAULT_TOKEN_PATH = Path.home() / ".broccoli" / "xai_oauth_tokens.json"


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str = ""
    expires_at: float = 0.0
    token_type: str = "Bearer"
    scope: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def expired(self) -> bool:
        return time.time() >= (self.expires_at - 60)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
            "scope": self.scope,
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenSet":
        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            expires_at=float(data.get("expires_at", 0) or 0),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope", ""),
            raw=data.get("raw", {}) or {},
        )


def _form_post(url: str, data: Dict[str, str], timeout: float = 20.0) -> Dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "broccoli-core/xai-oauth",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"xAI OAuth HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"xAI OAuth network error: {exc.reason}") from exc


def _get_json(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "broccoli-core/xai-oauth"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def discover() -> Dict[str, Any]:
    cached = getattr(discover, "_cache", None)
    if cached is None:
        cached = _get_json(DISCOVERY_URL)
        setattr(discover, "_cache", cached)
    return cached


def request_device_code() -> Dict[str, Any]:
    return _form_post(
        DEVICE_CODE_URL,
        {"client_id": CLIENT_ID, "scope": SCOPE},
    )


def poll_token(device_code: str, token_endpoint: str) -> Dict[str, Any]:
    return _form_post(
        token_endpoint,
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": CLIENT_ID,
            "device_code": device_code,
        },
    )


def refresh_token(tokens: TokenSet, token_endpoint: str) -> TokenSet:
    data = _form_post(
        token_endpoint,
        {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": tokens.refresh_token,
        },
    )
    return _token_from_response(data, fallback_refresh=tokens.refresh_token)


def _token_from_response(data: Dict[str, Any], fallback_refresh: str = "") -> TokenSet:
    expires_in = int(data.get("expires_in") or 3600)
    access = data.get("access_token", "")
    if not access:
        raise RuntimeError(f"xAI OAuth response missing access_token: {data}")
    return TokenSet(
        access_token=access,
        refresh_token=data.get("refresh_token") or fallback_refresh,
        expires_at=time.time() + expires_in,
        token_type=data.get("token_type", "Bearer"),
        scope=data.get("scope", SCOPE),
        raw=data,
    )


def load_tokens(path: Path = DEFAULT_TOKEN_PATH) -> Optional[TokenSet]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        tokens = TokenSet.from_dict(data)
        return tokens if tokens.access_token else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def save_tokens(tokens: TokenSet, path: Path = DEFAULT_TOKEN_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens.to_dict(), indent=2) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def clear_tokens(path: Path = DEFAULT_TOKEN_PATH) -> None:
    if path.exists():
        path.unlink()


def device_login(
    path: Path = DEFAULT_TOKEN_PATH,
    on_code: Optional[Callable[[str, str, int, int], None]] = None,
    timeout: float = 600.0,
) -> TokenSet:
    disc = discover()
    token_endpoint = disc.get("token_endpoint") or f"{ISSUER}/oauth2/token"
    device = request_device_code()

    verification_uri = device.get("verification_uri_complete") or device.get(
        "verification_uri", ""
    )
    user_code = device.get("user_code", "")
    device_code = device.get("device_code", "")
    if not device_code:
        raise RuntimeError(f"xAI OAuth did not return a device_code: {device}")
    interval = max(int(device.get("interval") or 5), 1)
    expires_in = int(device.get("expires_in") or 300)

    if on_code:
        on_code(verification_uri, user_code, interval, expires_in)
    else:
        print(f"Open: {verification_uri}")
        print(f"Code: {user_code}")
        print("Approve in the browser, then wait here.")

    deadline = time.time() + min(timeout, expires_in)
    while time.time() < deadline:
        time.sleep(interval)
        try:
            data = poll_token(device_code, token_endpoint)
        except RuntimeError as exc:
            msg = str(exc).lower()
            if "authorization_pending" in msg:
                continue
            if "slow_down" in msg:
                interval = min(interval + 5, 30)
                continue
            if "expired_token" in msg:
                raise RuntimeError(
                    "Device code expired — run the login again."
                ) from exc
            if "access_denied" in msg or "authorization_denied" in msg:
                raise RuntimeError("xAI login was denied.") from exc
            raise
        tokens = _token_from_response(data)
        save_tokens(tokens, path)
        return tokens

    raise RuntimeError("Device login timed out. Try again.")


def get_access_token(path: Path = DEFAULT_TOKEN_PATH) -> Optional[str]:
    tokens = load_tokens(path)
    if not tokens or not tokens.access_token:
        return None
    if not tokens.expired:
        return tokens.access_token
    if not tokens.refresh_token:
        return None
    try:
        disc = discover()
        token_endpoint = disc.get("token_endpoint") or f"{ISSUER}/oauth2/token"
        fresh = refresh_token(tokens, token_endpoint)
        save_tokens(fresh, path)
        return fresh.access_token
    except Exception:
        return None


def cmd_login(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else DEFAULT_TOKEN_PATH
    try:
        tokens = device_login(path=path)
    except Exception as exc:
        print(f"login failed: {exc}", file=sys.stderr)
        return 1
    print(f"Logged in. Access token expires at {tokens.expires_at:.0f}.")
    print(f"Tokens saved to {path} (mode 600).")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else DEFAULT_TOKEN_PATH
    tokens = load_tokens(path)
    if not tokens:
        print("No tokens found. Run: python -m runtime.providers.xai_oauth login")
        return 1
    print(f"access_token: {tokens.access_token[:12]}...")
    print(f"expires_at:   {tokens.expires_at:.0f} (expired={tokens.expired})")
    print(f"has_refresh:  {bool(tokens.refresh_token)}")
    print(f"path:         {path}")
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else DEFAULT_TOKEN_PATH
    clear_tokens(path)
    print(f"Cleared {path}.")
    return 0


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        prog="xai_oauth",
        description="xAI device-code OAuth login for Broccoli Core / Grok.",
    )
    p.add_argument(
        "--path",
        help="token file path (default: ~/.broccoli/xai_oauth_tokens.json)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("login", help="device-code login (headless-friendly)")
    s.set_defaults(func=cmd_login)

    s = sub.add_parser("status", help="show stored token status")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("logout", help="wipe stored tokens")
    s.set_defaults(func=cmd_logout)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
