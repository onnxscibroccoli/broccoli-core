# Implementation Plan

1. Add fail-closed ExecutionGuard state machine.
2. Add tests for missing/undated/CLEAR/TRIP/EXIT/WATCH/GONE behavior.
3. Add transition and illegal-verb tests.
4. Integrate guard before ProviderManager account/provider selection.
5. Verify GONE cannot become provider failover.
6. Run focused tests.
7. Run complete Broccoli test suite.
8. Stage only intentional guard integration files.
9. Commit and push.
