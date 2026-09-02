"""Production surface: grok CLI first, then OAuth HTTP + EventBus.

Does not boot the full accessibility / governor stack.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from runtime.eventbus.bus import EventBus
from runtime.providers import grok_cli
from runtime.providers import xai_oauth as xo
from runtime.providers.grok import GrokProvider


def make_provider(bus: Optional[EventBus] = None) -> GrokProvider:
    return GrokProvider(bus or EventBus())


def status_payload() -> Dict[str, Any]:
    tokens = xo.load_tokens()
    provider = make_provider()
    ready = provider.initialize()
    health = provider.health()
    return {
        "grok_cli_ready": grok_cli.cli_ready(),
        "grok_bin": str(grok_cli.grok_bin()) if grok_cli.grok_bin() else None,
        "oauth_path": str(xo.DEFAULT_TOKEN_PATH),
        "oauth_present": bool(tokens),
        "oauth_expired": bool(tokens.expired) if tokens else True,
        "oauth_has_refresh": bool(tokens and tokens.refresh_token),
        "provider_ready": ready,
        "provider_health": health,
    }


def ask(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    captured: List[Any] = []
    bus = EventBus()
    bus.subscribe("ProviderResult", lambda event: captured.append(event.payload))
    bus.subscribe("ProviderError", lambda event: captured.append({"error": event.payload}))
    provider = GrokProvider(bus)
    if not provider.initialize():
        return {
            "ok": False,
            "error": provider._last_error or "provider failed to initialize",
            "hint": "run: grok login --device-auth",
        }
    ok = provider.send(message, context=context)
    result: Dict[str, Any] = {
        "ok": ok,
        "auth": provider._auth_mode,
        "transport": provider._transport,
        "health": provider.health(),
    }
    if captured:
        result["event"] = captured[-1]
        if isinstance(captured[-1], dict):
            result["response"] = captured[-1].get("response") or captured[-1].get("error")
    if not ok and "error" not in result:
        result["error"] = provider._last_error
    return result


def cmd_status(_args: argparse.Namespace) -> int:
    payload = status_payload()
    print(json.dumps(payload, indent=2, default=str))
    return 0 if payload.get("provider_ready") else 1


def cmd_ask(args: argparse.Namespace) -> int:
    message = " ".join(args.message).strip()
    if not message:
        print("usage: broccoli ask <message>", file=sys.stderr)
        return 2
    result = ask(message)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("ok"):
            print(result.get("response") or "")
        else:
            print(result.get("error") or "ask failed", file=sys.stderr)
            hint = result.get("hint")
            if hint:
                print(hint, file=sys.stderr)
    return 0 if result.get("ok") else 1


def cmd_ping(args: argparse.Namespace) -> int:
    args.message = ["Reply with exactly: pong"]
    args.json = getattr(args, "json", False)
    return cmd_ask(args)


def cmd_login(args: argparse.Namespace) -> int:
    return xo.main(["login"] + (["--path", args.path] if args.path else []))


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        prog="broccoli",
        description="Production Broccoli Core CLI (grok CLI + live Grok).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="cli + oauth + provider health")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("ask", help="send a real prompt to Grok")
    s.add_argument("message", nargs="+")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("ping", help="live round-trip: ask Grok to reply pong")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_ping)

    s = sub.add_parser("login", help="device-code OAuth login (Broccoli tokens)")
    s.add_argument("--path", default=None)
    s.set_defaults(func=cmd_login)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
