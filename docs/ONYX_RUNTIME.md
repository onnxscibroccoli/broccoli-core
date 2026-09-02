# Onyx Runtime

Provider-agnostic orchestration layer. Does not know about Grok, xAI,
or any commercial ledger. Providers self-register; Onyx routes, fails
over, and emits EventBus telemetry.

```python
from runtime.onyx import OnyxRuntime
from runtime.providers.echo import EchoProvider

onyx = OnyxRuntime()
onyx.register("echo", EchoProvider())
onyx.ask("hello")  # -> {ok: True, ...}
```

No tokens. No network on the offline path. No human in the loop.
