# broccoli-core
Broccoli Core - Android Automation Framework 

---

# Organic Problem Solver

Broccoli Core now supports a provider-agnostic problem solving pipeline.

```
User Goal
      │
      ▼
Problem Runtime
      │
      ▼
Evidence Collectors
      │
      ▼
Reasoners
      │
      ▼
Remediation Planner
      │
      ▼
Workflow Engine
      │
      ▼
Verification
      │
      ▼
Knowledge Learning
```

Future collectors should publish evidence rather than directly solving problems.


## Runtime bridges

Clipboard input is handled by a passive bridge in `runtime/clipboard/`. The bridge publishes structured command and result envelopes to the shared EventBus, and the Governor can request a restart when bridge health goes stale or the bridge stops polling.


## Runtime bridges

Clipboard input is handled by a passive bridge in `runtime/clipboard/`. The bridge publishes structured command and result envelopes to the shared EventBus, and the Governor can request a restart when bridge health goes stale or the bridge stops polling.


## Runtime transports

Runtime components that expose `start()`, `stop()`, and `health()` are now managed as transports. The first transport is the clipboard bridge, which is registered with a transport registry, published on `TRANSPORT_HEALTH`, and supervised for restart/recovery by the Governor and transport supervisor.


## Runtime transports

Runtime components that expose `start()`, `stop()`, and `health()` are now managed as transports. The first transport is the clipboard bridge, which is registered with a transport registry, published on `TRANSPORT_HEALTH`, and supervised for restart/recovery by the Governor and transport supervisor.


## Runtime transports

Runtime components that expose `start()`, `stop()`, and `health()` are now managed as transports. The first transports are the accessibility driver and the clipboard bridge, both registered with the transport registry and supervised for restart/recovery by the Governor and transport supervisor.

