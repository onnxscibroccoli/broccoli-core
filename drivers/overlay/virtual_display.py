import time
from runtime.logger import setup_logger

class VirtualSecondaryDisplay:
    def __init__(self):
        self.logger = setup_logger("overlay")
        self.logger.info("🖥️  Virtual Secondary Display initialized")
        self.last_user_activity = time.time()
        self.idle_threshold = 30  # seconds of inactivity

    def update_activity(self):
        self.last_user_activity = time.time()

    def is_idle(self):
        return (time.time() - self.last_user_activity) > self.idle_threshold

    def show_prompt(self, message: str):
        if self.is_idle():
            self.logger.info(f"📺 Virtual Display: {message}")
            print(f"\n[Virtual Secondary Screen]\n{message}\n")
        else:
            self.logger.debug("User active - overlay suppressed")
