"""CLI entrypoint for the xAI OAuth device-code login.

Usage (from repo root, in Termux):
    python -m runtime.providers.xai_oauth login
    python -m runtime.providers.xai_oauth status
    python -m runtime.providers.xai_oauth logout
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from runtime.providers import xai_oauth as xo


def cmd_login(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else xo.DEFAULT_TOKEN_PATH
    try:
        tokens = xo.device_login(path=path)
    except Exception as exc:
        print(f"login failed: {exc}", file=sys.stderr)
        return 1
    print(f"Logged in. Access token expires at {tokens.expires_at:.0f}.")
    print(f"Tokens saved to {path} (mode 600).")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else xo.DEFAULT_TOKEN_PATH
    tokens = xo.load_tokens(path)
    if not tokens:
        print("No tokens found. Run: python -m runtime.providers.xai_oauth login")
        return 1
    print(f"access_token: {tokens.access_token[:12]}...")
    print(f"expires_at:   {tokens.expires_at:.0f} (expired={tokens.expired})")
    print(f"has_refresh:  {bool(tokens.refresh_token)}")
    print(f"path:         {path}")
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else xo.DEFAULT_TOKEN_PATH
    xo.clear_tokens(path)
    print(f"Cleared {path}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="xai_oauth")
    p.add_argument("--path", help="token file path (default: ~/.broccoli/xai_oauth_tokens.json)")
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
