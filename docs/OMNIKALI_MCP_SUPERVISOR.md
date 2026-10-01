# OmniKali MCP supervisor

The Android MCP executor lives beside `broccoli-core` in Termux because that is where the known-good Rish transport exists.

## Lifecycle contract

- MCP binds to `127.0.0.1:8787` only.
- Authentication uses the private `~/.config/omnikali/mcp.token` file.
- `bin/omnikali-mcp-supervisor` keeps the MCP process alive with bounded polling.
- A separate supervisor PID file and server PID file are used.
- A lock directory prevents duplicate supervisor instances.
- Termux:Boot launches the supervisor through the existing `broccoli-supervisor` boot entrypoint.
- A failed MCP process is recreated without restarting Broccoli's main runtime.

## Verification

On 2026-10-01 the MCP was intentionally terminated. The supervisor recreated it and a fresh MCP `initialize` request returned `serverInfo.name=omnikali-control-plane`, `version=0.1.0`.

A duplicate supervisor launch was also attempted and did not create a second supervisor because the lock was already held.

## Failure boundaries

Android process survival is not guaranteed by this mechanism. Termux:Boot and Android battery-management behavior remain platform dependencies. The supervisor provides recovery when it is running and when Termux permits it to run.
