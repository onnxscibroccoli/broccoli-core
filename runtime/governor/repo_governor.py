import subprocess
import threading
import time

from runtime.eventbus.service import bus


class RepoGovernor:
    def __init__(self, interval=5):
        self.interval = interval
        self.running = False

    def git(self, *args):
        try:
            return subprocess.check_output(
                ["git", *args],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            return ""

    def snapshot(self):
        branch = self.git("branch", "--show-current")
        ahead = 0

        status = self.git("status", "--porcelain=v2", "--branch")

        for line in status.splitlines():
            if line.startswith("# branch.ab"):
                parts = line.split()
                ahead = int(parts[2].replace("+", ""))

        changes = len(self.git("status", "--porcelain").splitlines())

        return {
            "branch": branch,
            "ahead": ahead,
            "changes": changes
        }

    def tick(self):
        while self.running:
            bus.publish(
                "repo.status",
                self.snapshot(),
                source="RepoGovernor"
            )
            time.sleep(self.interval)

    def start(self):
        self.running = True
        threading.Thread(
            target=self.tick,
            daemon=True
        ).start()

    def stop(self):
        self.running = False
