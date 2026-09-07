from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.surface.memory import MemorySurface
from runtime.watchme.record import WatchSession


def _default_path() -> Path:
    override = os.environ.get("BROCCOLI_WATCHME")
    if override:
        return Path(override)
    return Path.home() / ".broccoli" / "watchme" / "catalog.jsonl"


class WatchCatalog:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else _default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, demo: Dict[str, Any]) -> Dict[str, Any]:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(demo, ensure_ascii=False) + "\n")
        return demo

    def all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def get(self, demo_id: str) -> Optional[Dict[str, Any]]:
        for row in self.all():
            if row.get("id") == demo_id:
                return row
        return None

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return [
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "authorized": bool(row.get("authorized")),
                    "steps": len(row.get("steps") or []),
                }
                for row in self.all()
            ]
        parts = [p for p in re.split(r"\s+", q) if p]
        hits = []
        for row in self.all():
            blob = " ".join(
                [
                    str(row.get("title") or ""),
                    str(row.get("id") or ""),
                    " ".join(s.get("role", "") for s in row.get("steps") or []),
                    " ".join(s.get("text", "") for s in row.get("steps") or []),
                ]
            ).lower()
            if all(p in blob for p in parts):
                hits.append(
                    {
                        "id": row.get("id"),
                        "title": row.get("title"),
                        "authorized": bool(row.get("authorized")),
                        "steps": len(row.get("steps") or []),
                    }
                )
        return hits

    def record_and_save(
        self,
        title: str,
        steps: List[Dict[str, Any]],
        authorize: bool = True,
    ) -> Dict[str, Any]:
        ses = WatchSession(title)
        for step in steps:
            ses.record(
                action=str(step.get("action") or "observe"),
                role=str(step.get("role") or ""),
                text=str(step.get("text") or ""),
                semantic_id=str(step.get("semantic_id") or ""),
            )
        demo = ses.finish(authorize=authorize)
        return self.save(demo)

    def replay(self, demo_id: str, surface: Optional[MemorySurface] = None) -> Dict[str, Any]:
        demo = self.get(demo_id)
        if not demo:
            return {"ok": False, "code": "not_found", "id": demo_id}
        if not demo.get("authorized"):
            return {
                "ok": False,
                "code": "not_authorized",
                "message": "catalog this task with authorize=true once; then replay has prior auth",
                "id": demo_id,
            }
        surf = surface or MemorySurface(session="ready")
        events = [surf.create(provider_id="watchme").as_dict()]
        for step in demo.get("steps") or []:
            action = step.get("action")
            if action in ("navigate", "tap", "focus"):
                events.append(surf.focus().as_dict())
            elif action == "input":
                if not surf.inspect().focused:
                    events.append(surf.focus().as_dict())
                events.append(surf.input(str(step.get("text") or "")).as_dict())
            elif action == "submit":
                if not surf.inspect().focused:
                    events.append(surf.focus().as_dict())
                events.append(surf.submit().as_dict())
            elif action in ("observe", "wait"):
                events.append(surf.observe().as_dict())
            elif action == "back":
                events.append(surf.detach().as_dict())
                events.append(surf.attach().as_dict())
        failed = [e for e in events if not e.get("ok")]
        return {
            "ok": not failed,
            "id": demo_id,
            "title": demo.get("title"),
            "prior_auth": True,
            "events": events,
            "failed": failed,
        }
