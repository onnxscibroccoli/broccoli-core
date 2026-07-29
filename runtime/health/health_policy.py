from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthPolicy:
    heartbeat_interval_seconds: int = 60
    warning_age_multiplier: float = 1.0
    critical_age_multiplier: float = 2.0
    emit_heartbeat_when_stable: bool = True
    publish_transitions_only: bool = True

    def classify_age(self, age_seconds: float, max_age_seconds: int) -> str:
        if age_seconds <= max_age_seconds * self.warning_age_multiplier:
            return "healthy"
        if age_seconds <= max_age_seconds * self.critical_age_multiplier:
            return "warning"
        return "critical"
