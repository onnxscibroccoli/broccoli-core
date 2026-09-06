import unittest

from runtime.policy.execution_guard import (
    ExecutionDenied,
    ExecutionGuard,
    ExecutionHardStop,
    ExecutionState,
    IllegalExecutionVerb,
    IllegalTransition,
)


class ExecutionGuardTests(unittest.TestCase):

    def test_missing_state_is_no_go(self):
        guard = ExecutionGuard()
        with self.assertRaises(ExecutionDenied):
            guard.authorize()

    def test_undated_state_is_no_go(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=False)
        with self.assertRaises(ExecutionDenied):
            guard.authorize()

    def test_only_clear_authorizes(self):
        for state in (
            ExecutionState.TRIP,
            ExecutionState.EXIT,
            ExecutionState.WATCH,
        ):
            guard = ExecutionGuard()
            guard.set_state(state, dated=True)
            with self.subTest(state=state):
                with self.assertRaises(ExecutionDenied):
                    guard.authorize()

    def test_clear_authorizes_send(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=True)
        self.assertTrue(guard.authorize(verb="SEND"))

    def test_trip_denies_initial_fill(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.TRIP, dated=True)
        with self.assertRaises(ExecutionDenied):
            guard.authorize(initial_fill=True, verb="SEND")

    def test_exit_denies_initial_fill(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.EXIT, dated=True)
        with self.assertRaises(ExecutionDenied):
            guard.authorize(initial_fill=True, verb="SEND")

    def test_gone_is_hard_stop(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.GONE, dated=True)
        with self.assertRaises(ExecutionHardStop):
            guard.authorize()

    def test_clear_to_exit_is_illegal(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=True)
        with self.assertRaises(IllegalTransition):
            guard.set_state(ExecutionState.EXIT, dated=True)

    def test_state_progression_is_monotonic(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=True)
        guard.set_state(ExecutionState.TRIP, dated=True)
        guard.set_state(ExecutionState.EXIT, dated=True)
        guard.set_state(ExecutionState.WATCH, dated=True)
        guard.set_state(ExecutionState.GONE, dated=True)

        with self.assertRaises(ExecutionHardStop):
            guard.authorize()

    def test_illegal_execution_verb_raises(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=True)
        with self.assertRaises(IllegalExecutionVerb):
            guard.authorize(
                verb="ACCELERATE_OR_DCA_IF_LAGGARD_CHECKLIST"
            )

    def test_verb_is_normalized(self):
        guard = ExecutionGuard()
        guard.set_state(ExecutionState.CLEAR, dated=True)
        self.assertTrue(guard.authorize(verb=" send "))


if __name__ == "__main__":
    unittest.main()
