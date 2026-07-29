from pathlib import Path
import subprocess
import time
import shutil

from runtime.eventbus import EventBus


class RepoGovernor:
    """
    Native runtime repository observer.

    Replaces shell-based repo monitoring.
    """

    def __init__(
        self,
        bus: EventBus,
        root=None,
        interval=30
    ):
        self.bus = bus
        self.root = Path(root or Path.cwd())
        self.interval = interval
        self.running = False
        self.last_state = None


    def collect(self):
        branch = self._git(
            ["branch", "--show-current"]
        )

        status = self._git(
            ["status", "--short"]
        )

        ahead = self._ahead()

        disk = shutil.disk_usage(
            self.root
        )

        disk_percent = round(
            (disk.used / disk.total) * 100,
            2
        )

        return {
            "branch": branch,
            "ahead": ahead,
            "changes": len(
                [
                    x for x in status.splitlines()
                    if x.strip()
                ]
            ),
            "disk_percent": disk_percent
        }


    def _git(self, args):
        try:
            return subprocess.check_output(
                ["git"] + args,
                cwd=self.root,
                text=True
            ).strip()

        except Exception:
            return "unknown"


    def _ahead(self):
        try:
            result = subprocess.check_output(
                [
                    "git",
                    "rev-list",
                    "--count",
                    "@{u}..HEAD"
                ],
                cwd=self.root,
                text=True
            )

            return int(result.strip())

        except Exception:
            return 0


    def tick(self):

        state = self.collect()

        self.bus.publish(
            "repo.status",
            state,
            source="RepoGovernor"
        )


        if state["disk_percent"] >= 95:
            self.bus.publish(
                "repo.health",
                {
                    "condition":"disk_pressure",
                    "disk_percent":
                        state["disk_percent"]
                },
                source="RepoGovernor"
            )


        if self.last_state:
            if (
                state["changes"]
                != self.last_state["changes"]
            ):
                self.bus.publish(
                    "repo.drift",
                    {
                        "previous":
                            self.last_state,
                        "current":
                            state
                    },
                    source="RepoGovernor"
                )


        self.last_state = state


    def run_once(self):
        self.tick()


    def run_forever(self):

        self.running = True

        while self.running:
            self.tick()
            time.sleep(self.interval)


    def stop(self):
        self.running = False
