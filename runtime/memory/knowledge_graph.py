from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from runtime.eventbus.service import bus as default_bus

try:
    from runtime.event_bus.publisher import publish as write_event
except Exception:  # pragma: no cover
    def write_event(source, event, detail="", severity="INFO", metadata=None):
        return {
            "timestamp": int(time.time()),
            "source": source,
            "event": event,
            "severity": severity,
            "detail": detail,
            "metadata": metadata or {},
        }


KNOWLEDGE_TOPICS = {
    "KNOWLEDGE_READ",
    "KNOWLEDGE_WRITE",
    "KNOWLEDGE_HEARTBEAT",
    "KNOWLEDGE_UPDATED",
    "KNOWLEDGE_STORED",
    "KNOWLEDGE_FETCHED",
    "KNOWLEDGE_OK",
    "KNOWLEDGE_WARNING",
    "KNOWLEDGE_CRITICAL",
    "KNOWLEDGE_RECOVERED",
    "KNOWLEDGE_DEGRADED",
}


@dataclass
class KnowledgeNode:
    node_id: str
    content: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeEdge:
    source: str
    target: str
    relation: str = "relates_to"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeSnapshot:
    timestamp: int
    status: str
    node_count: int
    edge_count: int
    last_node_id: Optional[str] = None
    last_activity_age_seconds: Optional[float] = None
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "last_node_id": self.last_node_id,
            "last_activity_age_seconds": self.last_activity_age_seconds,
            "note": self.note,
            "metadata": dict(self.metadata),
        }


class KnowledgeGraph:
    """
    Persistent knowledge graph and health validator.

    The graph stores nodes and edges on disk, publishes knowledge events through
    the EventBus, and exposes a health snapshot that Governor modules can use in
    decision-making.
    """

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
        event_writer: Optional[Callable[..., Dict[str, Any]]] = None,
        warning_seconds: int = 120,
        critical_seconds: int = 300,
        heartbeat_interval_seconds: int = 60,
    ):
        self.bus = bus or default_bus
        self.root = Path(root or Path.cwd())
        self.event_writer = event_writer or write_event
        self.warning_seconds = warning_seconds
        self.critical_seconds = critical_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

        self.processed_dir = self.root / "runtime" / "event_bus" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.processed_dir / "knowledge_graph_state.json"
        self.started_at = time.time()
        self.last_activity_at: Optional[float] = None
        self.last_snapshot: Optional[KnowledgeSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False

        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []

        self._load_state()

        for topic in KNOWLEDGE_TOPICS:
            try:
                self.bus.subscribe(topic, self._on_event)
            except Exception:
                pass

    def _payload_of(self, event: Any) -> Dict[str, Any]:
        if event is None:
            return {}
        if isinstance(event, dict):
            return event
        payload = getattr(event, "payload", None)
        if isinstance(payload, dict):
            return payload
        try:
            return dict(event)
        except Exception:
            return {}

    def _topic_of(self, event: Any, payload: Dict[str, Any]) -> str:
        topic = getattr(event, "topic", None) or payload.get("topic") or payload.get("event")
        return str(topic or "UNKNOWN")

    def _on_event(self, event: Any) -> None:
        payload = self._payload_of(event)
        topic = self._topic_of(event, payload)
        self.last_activity_at = time.time()
        self._publish(topic, topic, severity="INFO", detail=f"Observed knowledge event: {topic}", metadata=payload)

    def _load_state(self) -> None:
        if not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text())
        except Exception:
            return

        for node_id, node_data in data.get("nodes", {}).items():
            if isinstance(node_data, dict):
                self.nodes[node_id] = KnowledgeNode(
                    node_id=node_id,
                    content=dict(node_data.get("content", {})),
                    tags=list(node_data.get("tags", [])),
                    metadata=dict(node_data.get("metadata", {})),
                    updated_at=int(node_data.get("updated_at", int(time.time()))),
                )

        for edge_data in data.get("edges", []):
            if isinstance(edge_data, dict):
                self.edges.append(
                    KnowledgeEdge(
                        source=str(edge_data.get("source", "")),
                        target=str(edge_data.get("target", "")),
                        relation=str(edge_data.get("relation", "relates_to")),
                        metadata=dict(edge_data.get("metadata", {})),
                        created_at=int(edge_data.get("created_at", int(time.time()))),
                    )
                )

        if self.nodes:
            self.last_activity_at = max(node.updated_at for node in self.nodes.values())

    def _save_state(self) -> None:
        payload = {
            "timestamp": int(time.time()),
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": {
                "started_at": int(self.started_at),
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
        }
        self.state_file.write_text(json.dumps(payload, indent=2))

    def _publish(
        self,
        topic: str,
        event: str,
        severity: str = "INFO",
        detail: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "timestamp": int(time.time()),
            "source": "knowledge_graph",
            "event": event,
            "severity": severity,
            "detail": detail,
            "metadata": metadata or {},
        }
        self.event_writer(
            source="knowledge_graph",
            event=event,
            detail=detail,
            severity=severity,
            metadata=metadata or {},
        )
        try:
            self.bus.publish(topic, payload, source="KnowledgeGraph")
        except Exception:
            pass
        out = self.processed_dir / f"knowledge_{int(time.time())}.json"
        try:
            out.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass
        return payload

    def _snapshot_status(self) -> Tuple[str, str, Optional[float]]:
        if self.last_activity_at is None:
            return "KNOWLEDGE_WARNING", "No knowledge activity yet.", None

        age = max(0.0, time.time() - self.last_activity_at)
        if age <= self.warning_seconds:
            return "KNOWLEDGE_OK", "Knowledge graph is fresh.", round(age, 2)
        if age <= self.critical_seconds:
            return "KNOWLEDGE_WARNING", "Knowledge graph is aging.", round(age, 2)
        return "KNOWLEDGE_CRITICAL", "Knowledge graph is stale.", round(age, 2)

    def upsert_node(
        self,
        node_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            node_id=node_id,
            content=dict(content),
            tags=list(tags or []),
            metadata=dict(metadata or {}),
            updated_at=int(time.time()),
        )
        self.nodes[node_id] = node
        self.last_activity_at = node.updated_at
        self._save_state()
        self._publish("KNOWLEDGE_WRITE", "KNOWLEDGE_WRITE", severity="INFO", detail=f"Wrote node {node_id}", metadata=node.to_dict())
        return node

    def read_node(self, node_id: str) -> Optional[KnowledgeNode]:
        node = self.nodes.get(node_id)
        if node is not None:
            self.last_activity_at = int(time.time())
            self._publish("KNOWLEDGE_READ", "KNOWLEDGE_READ", severity="INFO", detail=f"Read node {node_id}", metadata=node.to_dict())
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str = "relates_to",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEdge:
        edge = KnowledgeEdge(
            source=source,
            target=target,
            relation=relation,
            metadata=dict(metadata or {}),
            created_at=int(time.time()),
        )
        self.edges.append(edge)
        self.last_activity_at = edge.created_at
        self._save_state()
        self._publish("KNOWLEDGE_UPDATED", "KNOWLEDGE_UPDATED", severity="INFO", detail=f"Linked {source} -> {target}", metadata=edge.to_dict())
        return edge

    def verify_roundtrip(self) -> bool:
        token = f"probe_{int(time.time())}"
        payload = {
            "token": token,
            "purpose": "roundtrip_verification",
        }
        node = self.upsert_node(token, payload, tags=["probe", "verification"], metadata={"kind": "roundtrip"})
        loaded = self.read_node(token)
        ok = loaded is not None and loaded.content.get("token") == token
        self._publish(
            "KNOWLEDGE_HEARTBEAT" if ok else "KNOWLEDGE_CRITICAL",
            "KNOWLEDGE_HEARTBEAT" if ok else "KNOWLEDGE_CRITICAL",
            severity="INFO" if ok else "CRITICAL",
            detail="Knowledge roundtrip verification passed" if ok else "Knowledge roundtrip verification failed",
            metadata={"node": node.to_dict(), "ok": ok},
        )
        return ok

    def collect_health(self) -> KnowledgeSnapshot:
        status, note, age = self._snapshot_status()

        if self.state_file.exists():
            file_age = max(0.0, time.time() - self.state_file.stat().st_mtime)
            if file_age > self.critical_seconds:
                status = "KNOWLEDGE_CRITICAL"
                note = "Knowledge state file is stale."
                age = round(file_age, 2)
            elif file_age > self.warning_seconds and status == "KNOWLEDGE_OK":
                status = "KNOWLEDGE_WARNING"
                note = "Knowledge state file is aging."
                age = round(file_age, 2)

        return KnowledgeSnapshot(
            timestamp=int(time.time()),
            status=status,
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            last_node_id=next(reversed(self.nodes.keys())) if self.nodes else None,
            last_activity_age_seconds=age,
            note=note,
            metadata={
                "started_at": int(self.started_at),
                "warning_seconds": self.warning_seconds,
                "critical_seconds": self.critical_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
                "state_file": str(self.state_file),
            },
        )

    def decision_context(self) -> Dict[str, Any]:
        snapshot = self.collect_health()
        return {
            "knowledge_graph": snapshot.to_dict(),
            "node_count": snapshot.node_count,
            "edge_count": snapshot.edge_count,
            "ready_for_governor_decision": snapshot.status == "KNOWLEDGE_OK",
        }

    def _transition_events(self, previous: Optional[KnowledgeSnapshot], current: KnowledgeSnapshot):
        if previous is None:
            return [(current.status, current.status, current.note)]

        events = []
        if previous.status != current.status:
            events.append((current.status, current.status, current.note))
            if previous.status == "KNOWLEDGE_OK" and current.status in {"KNOWLEDGE_WARNING", "KNOWLEDGE_CRITICAL"}:
                events.append(("KNOWLEDGE_DEGRADED", "KNOWLEDGE_DEGRADED", current.note))
            if previous.status in {"KNOWLEDGE_WARNING", "KNOWLEDGE_CRITICAL"} and current.status == "KNOWLEDGE_OK":
                events.append(("KNOWLEDGE_RECOVERED", "KNOWLEDGE_RECOVERED", current.note))
        elif current.status == "KNOWLEDGE_OK" and (time.time() - self.last_emit_at) >= self.heartbeat_interval_seconds:
            events.append(("KNOWLEDGE_HEARTBEAT", "KNOWLEDGE_HEARTBEAT", current.note))

        return events

    def run_once(self) -> KnowledgeSnapshot:
        snapshot = self.collect_health()
        for topic, event, detail in self._transition_events(self.last_snapshot, snapshot):
            self._publish(topic, event, severity="INFO" if topic in {"KNOWLEDGE_OK", "KNOWLEDGE_RECOVERED", "KNOWLEDGE_HEARTBEAT"} else "WARNING", detail=detail, metadata=snapshot.to_dict())
        self.last_snapshot = snapshot
        self.last_emit_at = time.time()
        return snapshot

    def run_forever(self, interval_seconds: int = 60) -> None:
        self.running = True
        while self.running:
            self.run_once()
            time.sleep(interval_seconds)

    def stop(self) -> None:
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Broccoli Core Knowledge Graph")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--verify", action="store_true", help="Run a read/write roundtrip verification before exiting")
    args = parser.parse_args()

    graph = KnowledgeGraph()
    if args.verify:
        print(json.dumps({"verify_roundtrip": graph.verify_roundtrip()}, indent=2))
        return

    if args.loop:
        graph.run_forever(interval_seconds=args.interval)
    else:
        print(json.dumps(graph.run_once().to_dict(), indent=2))


if __name__ == "__main__":
    main()
