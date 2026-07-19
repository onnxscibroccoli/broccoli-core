import datetime
class Logger:
    def log(self, level, msg):
        ts = datetime.datetime.now().isoformat()
        print(f"[{ts}] [{level}] {msg}")


def setup_logger():
    return Logger()
