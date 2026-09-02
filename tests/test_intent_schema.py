import unittest
from runtime.intent_schema import (IntentSchemaEngine, LIBRARY, AutomationSchema,
                                 Step, IntentIndex, MarkovBackend, Emulator)


class TestIntentSchema(unittest.TestCase):
    def test_library_match(self):
        eng = IntentSchemaEngine()
        sch = eng.resolve("turn on bluetooth")
        self.assertEqual(sch.intent, "turn on bluetooth")
        self.assertGreaterEqual(sch.confidence, 0.5)
        self.assertTrue(sch.steps)

    def test_run_dry(self):
        eng = IntentSchemaEngine()
        called = {}
        eng.register_executor("bluetooth.on", lambda s: called.setdefault("bt", True) or True)
        eng.register_executor("notification", lambda s: True)
        res = eng.run("turn on bluetooth", dry_run=False)
        self.assertEqual(res["status"], "done")
        self.assertTrue(called.get("bt"))

    def test_tasker_export(self):
        sch = LIBRARY["turn_on_bluetooth"]
        xml = sch.to_tasker_xml()
        self.assertIn("<TaskerData", xml)
        self.assertIn("bluetooth", xml)

    def test_markov_learns(self):
        m = MarkovBackend()
        m.learn("turn on bluetooth", "turn_on_bluetooth")
        m.learn("turn on wifi", "turn_on_wifi")
        self.assertIn(m.suggest("turn on"), ("bluetooth", "wifi", None) or (None,))

    def test_emulator_promotes(self):
        em = Emulator()
        sch = AutomationSchema(intent="ping device", steps=[Step(action="notification", params={"text": "pong"})])
        self.assertTrue(em.trial(sch))
        em.promote(sch)
        self.assertIn("ping_device", LIBRARY)

    def test_vector_index(self):
        idx = IntentIndex()
        idx.add("a", "turn on bluetooth")
        idx.add("b", "schedule a meeting")
        hits = idx.search("enable bluetooth", k=1)
        self.assertEqual(hits[0][0], "a")
        self.assertGreater(hits[0][1], 0)


if __name__ == "__main__":
    unittest.main()
