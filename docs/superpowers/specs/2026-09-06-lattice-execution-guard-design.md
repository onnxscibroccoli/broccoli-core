# LATTICE Execution Guard — Broccoli Core

## Purpose

Introduce a provider-agnostic, fail-closed authorization boundary before
ProviderManager selects an account or provider.

## State machine

CLEAR -> TRIP -> EXIT -> WATCH -> GONE

Only dated CLEAR authorizes provider-bound execution.

- missing state: NO-GO
- undated state: NO-GO
- TRIP: deny, including initial fill
- EXIT: deny
- WATCH: deny
- GONE: hard stop
- CLEAR -> EXIT: illegal
- GONE is terminal
- illegal execution verbs raise

## Boundary

ExecutionGuard.authorize() runs before:

1. provider preference
2. AccountPool selection
3. provider initialization
4. provider execution
5. provider failover

Provider preference remains opportunistic.

Account rotation remains provider-agnostic.

Authentication credentials remain outside the repository.

No LATTICE investment, portfolio, market, sentiment, or broker logic is
imported into Broccoli Core.
