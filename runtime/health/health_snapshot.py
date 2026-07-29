from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ComponentHealth:
    name: str
    required: bool
    status: str
    path: Optional[str] = None
    age_seconds: Optional[float] = None
    note: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealthSnapshot:
    timestamp: int
    overall_status: str
    components: List[ComponentHealth] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["components"] = [c.to_dict() for c in self.components]
        return data

    @property
    def required_components(self) -> List[ComponentHealth]:
        return [c for c in self.components if c.required]

    @property
    def optional_components(self) -> List[ComponentHealth]:
        return [c for c in self.components if not c.required]
