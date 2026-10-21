import unittest
from governor.authorization import AgenticTakeoverGovernor

class TestAgenticTakeover(unittest.TestCase):
    def setUp(self):
        self.governor = AgenticTakeoverGovernor()

    def test_authorization_pass(self):
        self.assertTrue(self.governor.request_takeover(50.0))
        self.assertEqual(self.governor.state, "AUTHORIZED")

    def test_financial_gate_denial(self):
        self.assertFalse(self.governor.request_takeover(150.0))
        self.assertEqual(self.governor.state, "DENIED")

if __name__ == '__main__':
    unittest.main()
