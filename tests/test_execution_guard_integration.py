import unittest

from runtime.account_pool import Account, AccountPool
from runtime.providers.manager import ProviderManager
from runtime.policy.execution_guard import (
    ExecutionDenied,
    ExecutionGuard,
    ExecutionHardStop,
    ExecutionState,
)


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, *args, **kwargs):
        self.events.append((args, kwargs))


class FakeProvider:
    def __init__(self):
        self.sent = []
        self.initialized = 0

    def capabilities(self):
        return {}

    def initialize(self):
        self.initialized += 1

    def send(self, message):
        self.sent.append(message)
        return True

    def health(self):
        return {"status": "ok"}


class ExecutionGuardIntegrationTests(unittest.TestCase):

    def test_guard_denies_before_account_selection(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("grok-a", "grok"),
            Account("other-a", "other"),
        ])
        guard = ExecutionGuard()

        manager = ProviderManager(
            bus,
            account_pool=pool,
            execution_guard=guard,
        )

        provider = FakeProvider()
        manager.register_account("grok-a", provider)
        manager.register_account("other-a", provider)

        with self.assertRaises(ExecutionDenied):
            manager.send("blocked")

        self.assertEqual(provider.sent, [])

    def test_guard_denies_before_provider_preference(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("grok-a", "grok"),
            Account("other-a", "other"),
        ])
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.TRIP, dated=True)

        manager = ProviderManager(
            bus,
            account_pool=pool,
            execution_guard=guard,
        )

        provider = FakeProvider()
        manager.register_account("grok-a", provider)
        manager.register_account("other-a", provider)

        with self.assertRaises(ExecutionDenied):
            manager.send("blocked", preferred_provider="grok")

        self.assertEqual(provider.sent, [])

    def test_clear_allows_provider_manager_execution(self):
        bus = FakeBus()
        pool = AccountPool([Account("grok-a", "grok")])
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=True)

        manager = ProviderManager(
            bus,
            account_pool=pool,
            execution_guard=guard,
        )

        provider = FakeProvider()
        manager.register_account("grok-a", provider)

        self.assertTrue(manager.send("allowed"))
        self.assertEqual(provider.sent, ["allowed"])

    def test_gone_is_not_provider_failover(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("grok-a", "grok"),
            Account("other-a", "other"),
        ])
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.GONE, dated=True)

        manager = ProviderManager(
            bus,
            account_pool=pool,
            execution_guard=guard,
        )

        provider = FakeProvider()
        manager.register_account("grok-a", provider)
        manager.register_account("other-a", provider)

        with self.assertRaises(ExecutionHardStop):
            manager.send("must-stop")

        self.assertEqual(provider.sent, [])
        self.assertTrue(all(a.available for a in pool.accounts))


if __name__ == "__main__":
    unittest.main()
