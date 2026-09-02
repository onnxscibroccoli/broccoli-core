# Onyx Agentic Workflow

`OnyxRuntime.run_loop(goal)` drives an autonomous, event-driven loop:

1. Ask the routed provider (Echo offline, Grok CLI when logged in) for the next step.
2. Parse `NEXT:` / `DONE:` / `NEED_USER:` prefixes.
3. On `NEED_USER:`, pause and either return a pause payload or call `needs_user(question)`.
4. Emit `WorkflowStep`, `WorkflowComplete`, `WorkflowNeedsUser`, `WorkflowExhausted` on the EventBus.
5. Cap at `max_steps` so it can never spin forever.

## Why this exists

The ChatGPT principles review complained that the Grok CLI path was a
manual, provider-specific, commercial-dependent step. `run_loop` makes
the *workflow* autonomous and provider-agnostic: Echo proves the loop
with zero tokens, and Grok CLI is just one registered transport that
bills the SuperGrok weekly pool instead of the $0 API ledger.

## Direct HTTP to the subscription proxy

If you want to skip the CLI binary and call
`https://cli-chat-proxy.grok.com/v1` directly, use
`runtime.providers.grok_cli.proxy_headers(access_token)`. Those headers
(`X-XAI-Token-Auth: xai-grok-cli`, `x-grok-client-identifier: grok-shell`,
`x-grok-client-version`) are what make the proxy honor a SuperGrok OAuth
token instead of 402ing it.

## Next steps

- Wire `run_loop` into `bin/broccoli workflow <goal>`.
- Persist workflow state + step logs to the EventBus journal.
- Add a `needs_user` default that posts a GitHub issue comment when it
  can't decide.
