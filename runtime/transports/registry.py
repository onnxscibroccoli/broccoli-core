from __future__ import annotations

from collections import OrderedDict

from .events import TRANSPORT_HEALTH, TRANSPORT_RECOVERY_FAILED


class TransportRegistry:
    def __init__(self, bus):
        self.bus = bus
        self._transports = OrderedDict()

    def register(self, name, transport):
        self._transports[name] = transport
        return transport

    def get(self, name):
        return self._transports.get(name)

    def items(self):
        return self._transports.items()

    def start_all(self):
        for name, transport in self._transports.items():
            if not hasattr(transport, "start"):
                continue
            try:
                transport.start()
            except Exception as exc:
                self.bus.publish(
                    TRANSPORT_RECOVERY_FAILED,
                    {
                        "transport": name,
                        "phase": "start_all",
                        "error": str(exc),
                    },
                    source="TransportRegistry",
                )

    def stop_all(self):
        for name, transport in reversed(list(self._transports.items())):
            if not hasattr(transport, "stop"):
                continue
            try:
                transport.stop()
            except Exception as exc:
                self.bus.publish(
                    TRANSPORT_RECOVERY_FAILED,
                    {
                        "transport": name,
                        "phase": "stop_all",
                        "error": str(exc),
                    },
                    source="TransportRegistry",
                )

    def restart(self, name):
        transport = self.get(name)
        if transport is None:
            raise KeyError(name)

        if hasattr(transport, "stop"):
            transport.stop()
        if hasattr(transport, "start"):
            transport.start()
        return transport

    def health(self, name=None):
        if name is not None:
            transport = self.get(name)
            if transport is None:
                return {
                    "transport": name,
                    "registered": False,
                    "running": False,
                }

            payload = transport.health() if hasattr(transport, "health") else {}
            return {
                "transport": name,
                "registered": True,
                **payload,
            }

        return {
            transport_name: self.health(transport_name)
            for transport_name in self._transports
        }

    def publish_health(self):
        reports = []
        for name, transport in self._transports.items():
            payload = transport.health() if hasattr(transport, "health") else {}
            report = {
                "transport": name,
                **payload,
            }
            self.bus.publish(
                TRANSPORT_HEALTH,
                report,
                source="TransportRegistry",
            )
            reports.append(report)
        return reports
