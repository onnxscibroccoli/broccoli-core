import time
from runtime.logger import setup_logger

class VirtualSecondaryDisplay:
    def __init__(self):
        self.logger = setup_logger("overlay")
        self.logger.info("🖥️  Virtual Secondary Display initialized")
        self.last_user_activity = time.time()
        self.idle_threshold = 30  # seconds

    def is_idle(self):
        return (time.time() - self.last_user_activity) > self.idle_threshold

    def update_activity(self):
        self.last_user_activity = time.time()

    def show_prompt(self, message: str):
        if self.is_idle():
            self.logger.info(f"📺 Virtual Display Prompt: {message}")
            # In future: show via overlay service, notification, or floating window
            print(f"\n[Virtual Screen] {message}\n")
        else:
            self.logger.info("User active - suppressing overlay")
