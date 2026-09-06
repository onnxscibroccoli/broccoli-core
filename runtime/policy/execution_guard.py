"""Fail-closed, provider-agnostic execution authorization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionState(str, Enum):
    CLEAR = "CLEAR"
    TRIP = "TRIP"
    EXIT = "EXIT"
    WATCH = "WATCH"
    GONE = "GONE"


@dataclass(frozen=True)
class GuardRecord:
    state: ExecutionState
    dated: bool = True


class ExecutionDenied(RuntimeError):
    """Execution is not authorized."""


class ExecutionHardStop(ExecutionDenied):
    """GONE state permanently blocks execution."""


class IllegalTransition(ValueError):
    """Requested execution-state transition is illegal."""


class IllegalExecutionVerb(ValueError):
    """Requested execution verb is not permitted."""


class ExecutionGuard:
    """Deterministic fail-closed execution state machine."""

    _ORDER = {
        ExecutionState.CLEAR: 0,
        ExecutionState.TRIP: 1,
        ExecutionState.EXIT: 2,
        ExecutionState.WATCH: 3,
        ExecutionState.GONE: 4,
    }

    _ALLOWED_VERBS = frozenset({"SEND"})

    def __init__(self, record: GuardRecord | None = None) -> None:
        self._record = record

    @property
    def record(self) -> GuardRecord | None:
        return self._record

    @property
    def state(self) -> ExecutionState | None:
        return None if self._record is None else self._record.state

    def set_state(
        self,
        state: ExecutionState | str,
        *,
        dated: bool = True,
    ) -> GuardRecord:
        state = self._coerce_state(state)

        if self._record is not None:
            previous = self._record.state

            if state != previous:
                previous_rank = self._ORDER[previous]
                new_rank = self._ORDER[state]

                if new_rank != previous_rank + 1:
                    raise IllegalTransition(
                        f"illegal execution-state transition: "
                        f"{previous.value} -> {state.value}"
                    )

        self._record = GuardRecord(
            state=state,
            dated=dated,
        )
        return self._record

    def authorize(
        self,
        *,
        initial_fill: bool = False,
        verb: str = "SEND",
    ) -> bool:
        normalized_verb = str(verb).strip().upper()

        if normalized_verb not in self._ALLOWED_VERBS:
            raise IllegalExecutionVerb(
                f"illegal execution verb: {normalized_verb!r}"
            )

        record = self._record

        if record is None:
            raise ExecutionDenied(
                "execution guard has no state: NO-GO"
            )

        if not record.dated:
            raise ExecutionDenied(
                "execution guard state is undated: NO-GO"
            )

        if record.state is ExecutionState.GONE:
            raise ExecutionHardStop(
                "execution guard is GONE: hard stop"
            )

        if record.state is not ExecutionState.CLEAR:
            raise ExecutionDenied(
                f"execution guard state {record.state.value}: NO-GO"
            )

        # Explicitly accepted but never used as a bypass.
        _ = initial_fill

        return True

    @staticmethod
    def _coerce_state(
        state: ExecutionState | str,
    ) -> ExecutionState:
        if isinstance(state, ExecutionState):
            return state

        try:
            return ExecutionState(str(state).strip().upper())
        except ValueError as exc:
            raise ValueError(
                f"unknown execution state: {state!r}"
            ) from exc
