import time
from runtime.logger import setup_logger
from runtime.metrics import Metrics

class Daemon:
    def __init__(self):
        self.logger = setup_logger("daemon")
        self.metrics = Metrics()
        self.running = False

    def start(self):
        self.running = True
        self.logger.info("Broccoli Daemon started")
        try:
            while self.running:
                self.metrics.increment("cycle")
                self.logger.info(f"Governor cycle {self.metrics.cycles}")
                time.sleep(2)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        self.logger.info("Daemon stopped")
