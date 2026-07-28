"""Semantic snapshot diff → normalized events."""

from __future__ import annotations
from typing import Any, Dict, List
from .events import SemanticEvent, SemanticEventType, make_event


def diff_snapshots(prev: Dict[str, Any], curr: Dict[str, Any]) -> List[SemanticEvent]:
    """
    Compare two cache snapshots and emit only meaningful semantic events.
    Both snapshots are the dict form returned by SemanticCache.snapshot().
    """
    events: List[SemanticEvent] = []
    if not prev:
        prev = {"nodes": {}, "focused_id": None, "package": "", "window_id": -1, "screen_id": ""}

    prev_nodes = prev.get("nodes") or {}
    curr_nodes = curr.get("nodes") or {}
    package = curr.get("package") or ""
    window_id = int(curr.get("window_id", -1))

    prev_ids = set(prev_nodes)
    curr_ids = set(curr_nodes)

    # NODE_ADDED / NODE_REMOVED / NODE_UPDATED
    for sid in curr_ids - prev_ids:
        n = curr_nodes[sid]
        events.append(make_event(
            SemanticEventType.NODE_ADDED,
            package=package,
            window_id=window_id,
            stable_id=sid,
            confidence=0.9,
            class_name=n.get("class_name", ""),
            text=n.get("text", ""),
            bounds=n.get("bounds"),
        ))

    for sid in prev_ids - curr_ids:
        events.append(make_event(
            SemanticEventType.NODE_REMOVED,
            package=package,
            window_id=window_id,
            stable_id=sid,
            confidence=0.95,
        ))

    for sid in prev_ids & curr_ids:
        p = prev_nodes[sid]
        c = curr_nodes[sid]
        if p.get("fingerprint") != c.get("fingerprint"):
            events.append(make_event(
                SemanticEventType.NODE_UPDATED,
                package=package,
                window_id=window_id,
                stable_id=sid,
                confidence=0.85,
                before={"text": p.get("text"), "bounds": p.get("bounds"), "focused": p.get("focused")},
                after={"text": c.get("text"), "bounds": c.get("bounds"), "focused": c.get("focused")},
            ))

    # FOCUS_CHANGED
    prev_focus = prev.get("focused_id")
    curr_focus = curr.get("focused_id")
    if prev_focus != curr_focus:
        events.append(make_event(
            SemanticEventType.FOCUS_CHANGED,
            package=package,
            window_id=window_id,
            stable_id=curr_focus or "",
            confidence=0.95,
            previous=prev_focus,
            current=curr_focus,
        ))

    # WINDOW_CHANGED
    if prev.get("window_id") != curr.get("window_id"):
        events.append(make_event(
            SemanticEventType.WINDOW_CHANGED,
            package=package,
            window_id=window_id,
            confidence=0.9,
            previous_window=prev.get("window_id"),
            current_window=window_id,
        ))

    # SCREEN_CHANGED
    if prev.get("screen_id") != curr.get("screen_id") and curr.get("screen_id"):
        events.append(make_event(
            SemanticEventType.SCREEN_CHANGED,
            package=package,
            window_id=window_id,
            confidence=0.9,
            previous_screen=prev.get("screen_id"),
            current_screen=curr.get("screen_id"),
        ))

    # CONTENT_CHANGED / SCROLL_CHANGED heuristics from node updates
    if any(e.event_type == SemanticEventType.NODE_UPDATED for e in events):
        # If any bounds changed significantly, treat as possible scroll
        scroll_like = False
        for e in events:
            if e.event_type != SemanticEventType.NODE_UPDATED:
                continue
            before = e.payload.get("before") or {}
            after = e.payload.get("after") or {}
            b1, b2 = before.get("bounds"), after.get("bounds")
            if b1 and b2 and b1 != b2:
                # vertical shift dominant → scroll signal
                dy = abs((b2[1] if len(b2) > 1 else 0) - (b1[1] if len(b1) > 1 else 0))
                if dy > 8:
                    scroll_like = True
                    break
        if scroll_like:
            events.append(make_event(
                SemanticEventType.SCROLL_CHANGED,
                package=package,
                window_id=window_id,
                confidence=0.7,
            ))
        else:
            events.append(make_event(
                SemanticEventType.CONTENT_CHANGED,
                package=package,
                window_id=window_id,
                confidence=0.75,
            ))

    # Aggregate UI_CHANGED when anything meaningful happened
    if events:
        events.append(make_event(
            SemanticEventType.UI_CHANGED,
            package=package,
            window_id=window_id,
            confidence=0.8,
            change_count=len(events),
            types=[e.event_type.value for e in events],
        ))

    return events
