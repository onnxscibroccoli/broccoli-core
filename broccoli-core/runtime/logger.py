import datetime
class Logger:
    def log(self, level, msg, component=None):
        ts = datetime.datetime.now().isoformat()
        prefix = f"[{ts}] [{level}]"
        if component:
            prefix += f" [{component}]"
        print(f"{prefix} {msg}")
