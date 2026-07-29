from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    pattern: str
    required: bool = True
    max_age_seconds: int = 300
    note: str = ""


def default_component_specs() -> List[ComponentSpec]:
    """
    Required = must be present and fresh for the runtime to be considered healthy.
    Optional = tracked now, but missing data is not considered a hard failure yet.
    """
    return [
        ComponentSpec(
            name="repository_health",
            pattern="runtime/event_bus/processed/repo_*.json",
            required=True,
            max_age_seconds=900,
            note="Repository Health reports",
        ),
        ComponentSpec(
            name="drive_sync",
            pattern=".drive_sync/sync.log",
            required=True,
            max_age_seconds=900,
            note="Drive sync daemon log",
        ),
        ComponentSpec(
            name="event_bus",
            pattern="runtime/event_bus/processed/*.json",
            required=True,
            max_age_seconds=300,
            note="Runtime event stream artifacts",
        ),
        ComponentSpec(
            name="accessibility",
            pattern="runtime/event_bus/processed/accessibility_*.json",
            required=False,
            max_age_seconds=300,
            note="Accessibility telemetry (deferred until fully instrumented)",
        ),
        ComponentSpec(
            name="workflow",
            pattern="runtime/event_bus/processed/workflow_*.json",
            required=False,
            max_age_seconds=300,
            note="Workflow telemetry (deferred until fully instrumented)",
        ),
        ComponentSpec(
            name="scheduler",
            pattern="runtime/event_bus/processed/scheduler_*.json",
            required=False,
            max_age_seconds=300,
            note="Scheduler telemetry (deferred until fully instrumented)",
        ),
        ComponentSpec(
            name="knowledge_graph",
            pattern="runtime/event_bus/processed/knowledge_*.json",
            required=False,
            max_age_seconds=300,
            note="Knowledge graph telemetry (deferred until fully instrumented)",
        ),
        ComponentSpec(
            name="metrics",
            pattern="runtime/event_bus/processed/metrics_*.json",
            required=False,
            max_age_seconds=300,
            note="Metrics telemetry (deferred until fully instrumented)",
        ),
    ]
