import unittest

from runtime.account_pool import Account, AccountPool


class AccountPoolTests(unittest.TestCase):

    def make_pool(self):
        return AccountPool([
            Account("a", "provider_a"),
            Account("b", "provider_b"),
            Account("c", "provider_c"),
        ])

    def test_round_robin(self):
        pool = self.make_pool()

        selected = [
            pool.select().account_id
            for _ in range(6)
        ]

        self.assertEqual(
            selected,
            ["a", "b", "c", "a", "b", "c"],
        )

    def test_skips_unavailable_account(self):
        pool = self.make_pool()
        pool.mark_unavailable("b")

        selected = [
            pool.select().account_id
            for _ in range(6)
        ]

        self.assertEqual(
            selected,
            ["a", "c", "a", "c", "a", "c"],
        )

    def test_cooldown_skips_account_until_expired(self):
        pool = self.make_pool()

        pool.cooldown("b", 10, now=100)

        self.assertEqual(pool.select(now=100).account_id, "a")
        self.assertEqual(pool.select(now=100).account_id, "c")
        self.assertEqual(pool.select(now=100).account_id, "a")

        # Cooldown has expired.
        self.assertEqual(pool.select(now=110).account_id, "b")

    def test_mark_available_clears_cooldown(self):
        pool = self.make_pool()

        pool.mark_unavailable("b")
        pool.cooldown("b", 100, now=100)

        pool.mark_available("b")

        self.assertTrue(pool.accounts[1].available)
        self.assertEqual(pool.accounts[1].cooldown_until, 0.0)

    def test_empty_pool_returns_none(self):
        pool = AccountPool()

        self.assertIsNone(pool.select())

    def test_duplicate_account_id_rejected(self):
        pool = self.make_pool()

        with self.assertRaises(ValueError):
            pool.add(Account("a", "another_provider"))

    def test_unknown_account_rejected(self):
        pool = self.make_pool()

        with self.assertRaises(KeyError):
            pool.mark_unavailable("does-not-exist")

    def test_negative_cooldown_rejected(self):
        pool = self.make_pool()

        with self.assertRaises(ValueError):
            pool.cooldown("a", -1)


if __name__ == "__main__":
    unittest.main()
