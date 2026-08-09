import logging

from .health import check
from . import actions


logger = logging.getLogger("shizuku.driver")


class ShizukuDriver:

    def __init__(self, bus=None):
        self.bus = bus
        self.status = check()

        self._publish_status()

    def _publish_status(self):
        if self.bus:
            self.bus.publish(
                "CAPABILITY_STATUS",
                {
                    "capability": "shizuku",
                    **self.status
                },
                source="ShizukuDriver"
            )

    def health(self):
        return self.status

    def tap(self, x, y):
        return actions.tap(x, y)

    def text(self, value):
        return actions.text(value)
