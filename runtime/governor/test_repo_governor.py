import time

from runtime.eventbus.service import bus
from runtime.governor.repo_governor import RepoGovernor


def printer(event):
    print(event.topic, event.payload)

bus.subscribe("repo.status", printer)

g = RepoGovernor(interval=2)
g.start()

time.sleep(7)

g.stop()

print("PASS")
