from typing import Optional
from constants import (
    STATE_INIT, 
    STATE_RUNNING, 
    STATE_PAUSED, 
    STATE_ERROR, 
    STATE_STOPPED
)

class SystemState:
    def __init__(self):
        self._current_state: str = STATE_INIT
        self.last_error: Optional[Exception] = None

    @property
    def current_state(self) -> str:
        return self._current_state

    def transition_to(self, new_state: str, reason: str = "") -> bool:
        """
        Safely transitions the system to a new state.
        Returns True if the transition was successful.
        """
        valid_states = {
            STATE_INIT, STATE_RUNNING, STATE_PAUSED, 
            STATE_ERROR, STATE_STOPPED
        }
        
        if new_state not in valid_states:
            print(f"[State] Invalid state requested: {new_state}")
            return False

        old_state = self._current_state
        self._current_state = new_state
        
        transition_msg = f"{old_state} -> {new_state}"
        if reason:
            transition_msg += f" ({reason})"
            
        print(f"[State] Transition: {transition_msg}")
        return True

    def set_error(self, error: Exception) -> None:
        """Helper to transition to an error state and capture the exception."""
        self.last_error = error
        self.transition_to(STATE_ERROR, str(error))
