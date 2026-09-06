import unittest

from runtime.account_pool import Account, AccountPool
from runtime.providers.manager import ProviderManager


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, name, payload, source=None):
        self.events.append((name, payload, source))


class FakeProvider:
    def __init__(self, result=True):
        self.result = result
        self.messages = []
        self.initialized = 0

    def initialize(self):
        self.initialized += 1

    def send(self, message):
        self.messages.append(message)
        return self.result

    def health(self):
        return {"status": "ok"}

    def capabilities(self):
        return {"send": True}


class ProviderAccountPoolTests(unittest.TestCase):

    def test_manager_can_register_multiple_authorized_accounts(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("grok-1", "grok"),
            Account("gemini-1", "gemini"),
        ])
        manager = ProviderManager(bus, account_pool=pool)

        grok = FakeProvider()
        gemini = FakeProvider()

        manager.register_account("grok-1", grok)
        manager.register_account("gemini-1", gemini)

        self.assertTrue(manager.send("one"))
        self.assertTrue(manager.send("two"))

        self.assertEqual(grok.messages, ["one"])
        self.assertEqual(gemini.messages, ["two"])

    def test_round_robin_skips_unavailable_account(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("grok-1", "grok"),
            Account("grok-2", "grok"),
            Account("gemini-1", "gemini"),
        ])
        manager = ProviderManager(bus, account_pool=pool)

        p1 = FakeProvider()
        p2 = FakeProvider()
        p3 = FakeProvider()

        manager.register_account("grok-1", p1)
        manager.register_account("grok-2", p2)
        manager.register_account("gemini-1", p3)

        pool.mark_unavailable("grok-2")

        self.assertTrue(manager.send("one"))
        self.assertTrue(manager.send("two"))

        self.assertEqual(p1.messages, ["one"])
        self.assertEqual(p2.messages, [])
        self.assertEqual(p3.messages, ["two"])

    def test_preferred_provider_is_used_first_when_available(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("gemini-1", "gemini"),
            Account("grok-1", "grok"),
        ])
        manager = ProviderManager(bus, account_pool=pool)

        gemini = FakeProvider()
        grok = FakeProvider()

        manager.register_account("gemini-1", gemini)
        manager.register_account("grok-1", grok)

        self.assertTrue(
            manager.send("hello", preferred_provider="grok")
        )

        self.assertEqual(grok.messages, ["hello"])
        self.assertEqual(gemini.messages, [])

    def test_failed_account_is_marked_unavailable_and_next_account_is_used(self):
        bus = FakeBus()
        pool = AccountPool([
            Account("grok-1", "grok"),
            Account("grok-2", "grok"),
        ])
        manager = ProviderManager(bus, account_pool=pool)

        failed = FakeProvider(result=False)
        healthy = FakeProvider(result=True)

        manager.register_account("grok-1", failed)
        manager.register_account("grok-2", healthy)

        self.assertTrue(manager.send("hello"))

        self.assertEqual(failed.messages, ["hello"])
        self.assertEqual(healthy.messages, ["hello"])
        self.assertFalse(pool.accounts[0].available)

    def test_manager_without_account_pool_preserves_existing_behavior(self):
        bus = FakeBus()
        manager = ProviderManager(bus)

        provider = FakeProvider()
        manager.register("grok", provider)

        self.assertTrue(manager.send("hello"))
        self.assertEqual(provider.messages, ["hello"])


    def test_manager_delegates_account_selection_to_pool_public_api(self):
        from unittest.mock import Mock
        from runtime.account_pool import Account
        from runtime.providers.manager import ProviderManager

        pool = Mock()
        selected = Account("grok-a", "grok")
        pool.select.return_value = selected

        manager = ProviderManager(FakeBus(), account_pool=pool)

        provider = Mock()
        provider.send.return_value = True
        manager.providers["grok"] = provider
        manager.account_providers["grok-a"] = provider

        self.assertTrue(manager.send("hello", preferred_provider="grok"))

        pool.select.assert_called_once_with(
            preferred_provider="grok",
        )

    def test_account_pool_can_prefer_provider_without_exposing_cursor(self):
        from runtime.account_pool import Account, AccountPool

        pool = AccountPool([
            Account("grok-a", "grok"),
            Account("other-a", "other"),
        ])

        selected = pool.select(preferred_provider="other")

        self.assertIsNotNone(selected)
        self.assertEqual(selected.account_id, "other-a")

    def test_account_pool_public_selection_preserves_round_robin(self):
        from runtime.account_pool import Account, AccountPool

        pool = AccountPool([
            Account("grok-a", "grok"),
            Account("grok-b", "grok"),
            Account("other-a", "other"),
        ])

        self.assertEqual(pool.select().account_id, "grok-a")
        self.assertEqual(
            pool.select(preferred_provider="other").account_id,
            "other-a",
        )
        self.assertEqual(pool.select().account_id, "grok-b")
if __name__ == "__main__":
    unittest.main(verbosity=2)
