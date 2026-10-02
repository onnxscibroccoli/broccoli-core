#!/usr/bin/env python3
"""Ruto-backed Android virtual surface for Broccoli Core.

The proven path is Android VirtualDisplayAdapter via Ruto/Shizuku.
Do not use overlay display settings or direct display ActivityManager launches:
live tests showed they can create task records without a durable app window.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import re
import shlex
import time
from typing import Any, Optional
import xml.etree.ElementTree as ET

from runtime.surface.protocol import SurfaceEvent, SurfaceState
from tools.android_transport import RishTransport

RUTO_PACKAGE = "com.rosan.ruto"
RUTO_ACTIVITY = "com.rosan.ruto/.ui.activity.MainActivity"
RUTO_DISPLAY_NAME = "Virtual Screen"
RUTO_OWNER = "com.android.shell"
UI_DUMP = "/sdcard/OmniKali/ui/ruto-ui.xml"
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


@dataclass(frozen=True)
class DisplayRecord:
    display_id: int
    name: str
    owner: str
    private: bool


@dataclass(frozen=True)
class SurfaceProbe:
    display_id: Optional[int]
    display: bool
    task: bool
    process: bool
    window: bool
    surface: bool

    @property
    def healthy(self) -> bool:
        return all((self.display, self.task, self.process, self.window, self.surface))
    def as_dict(self) -> dict[str, Any]:
        return {
            "display_id": self.display_id,
            "display": self.display,
            "task": self.task,
            "process": self.process,
            "window": self.window,
            "surface": self.surface,
            "healthy": self.healthy,
        }


def parse_ruto_displays(raw: str) -> list[DisplayRecord]:
    records: list[DisplayRecord] = []
    pattern = re.compile(
        r'mBaseDisplayInfo=DisplayInfo\{"(?P<name>[^"]+)", displayId '
        r'(?P<id>\d+).*?owner (?P<owner>[A-Za-z0-9._]+)'
    )
    for line in raw.splitlines():
        if "mBaseDisplayInfo=DisplayInfo" not in line:
            continue
        match = pattern.search(line)
        if not match:
            continue
        name = match.group("name")
        owner = match.group("owner")
        if name != RUTO_DISPLAY_NAME or owner != RUTO_OWNER:
            continue
        records.append(
            DisplayRecord(
                display_id=int(match.group("id")),
                name=name,
                owner=owner,
                private="FLAG_PRIVATE" in line,
            )
        )
    return records


def display_block(raw: str, display_id: int) -> str:
    match = re.search(
        rf"(?ms)^\s*displayId={int(display_id)}\s*$.*?"
        rf"(?=^\s*displayId=\d+\s*$|\Z)",
        raw,
    )
    return match.group(0) if match else ""


def task_on_display(raw: str, package: str, display_id: int) -> bool:
    return package in display_block(raw, display_id)
def window_on_display(raw: str, package: str, display_id: int) -> bool:
    for block in re.split(r"(?m)^\s*Window #\d+ ", raw):
        if package not in block or f"mDisplayId={display_id}" not in block:
            continue
        if "mHasSurface=true" not in block or "HAS_DRAWN" not in block:
            continue
        if "isVisible=true" in block or "Surface: shown=true" in block:
            return True
    return False


def surface_on_display(raw: str, package: str, display_id: int) -> bool:
    marker = f'Display {display_id} name="{RUTO_DISPLAY_NAME}"'
    return package in raw and marker in raw


def _bounds(value: str) -> Optional[tuple[int, int, int, int]]:
    match = BOUNDS_RE.fullmatch(value or "")
    if not match:
        return None
    return tuple(int(x) for x in match.groups())


def semantic_center(xml_text: str, label: str) -> Optional[tuple[int, int]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    parent = {child: node for node in root.iter() for child in node}
    for node in root.iter("node"):
        if node.attrib.get("text") != label and node.attrib.get("content-desc") != label:
            continue
        target = node
        cur = node
        while cur in parent:
            if cur.attrib.get("clickable") == "true" and _bounds(cur.attrib.get("bounds", "")):
                target = cur
                break
            cur = parent[cur]
        box = _bounds(target.attrib.get("bounds", "")) or _bounds(node.attrib.get("bounds", ""))
        if box:
            x1, y1, x2, y2 = box
            return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


class RishSurface:
    """VirtualSurface implementation using Ruto + Shizuku/Rish."""

    def __init__(self, backend: Optional[Any] = None, sleeper=None) -> None:
        self.backend = backend or RishTransport(timeout=30)
        self.sleep = sleeper or time.sleep
        self.provider_id = ""
        self.display_id: Optional[int] = None
        self._attached = False
        self._focused = False

    @staticmethod
    def _package(value: str) -> str:
        if not PACKAGE_RE.fullmatch(value):
            raise ValueError("invalid Android package name")
        return value

    def _run(self, command: str):
        result = self.backend.run(command)
        ok = getattr(result, "ok", getattr(result, "returncode", 1) == 0)
        if not ok:
            raise RuntimeError(getattr(result, "combined_output", "Android shell command failed"))
        return result

    def _stdout(self, command: str) -> str:
        return str(getattr(self._run(command), "stdout", ""))

    def _displays(self) -> list[DisplayRecord]:
        return parse_ruto_displays(self._stdout("dumpsys display"))

    def _probe(self, package: str, preferred: Optional[int] = None) -> SurfaceProbe:
        displays = self._displays()
        ids = [d.display_id for d in displays]
        if preferred is not None and preferred in ids:
            ids = [preferred] + [x for x in ids if x != preferred]
        activity = self._stdout("dumpsys activity activities")
        windows = self._stdout("dumpsys window windows")
        surfaces = self._stdout("dumpsys SurfaceFlinger --list")
        proc = self._stdout(f"pidof {shlex.quote(package)} 2>/dev/null || true").strip()
        for display_id in ids:
            probe = SurfaceProbe(
                display_id=display_id,
                display=True,
                task=task_on_display(activity, package, display_id),
                process=bool(proc),
                window=window_on_display(windows, package, display_id),
                surface=surface_on_display(surfaces, package, display_id),
            )
            if probe.healthy:
                return probe
        return SurfaceProbe(
            display_id=preferred if preferred in ids else (ids[0] if ids else None),
            display=bool(ids),
            task=False,
            process=bool(proc),
            window=False,
            surface=False,
        )
    def _dump_ui(self) -> str:
        command = (
            "mkdir -p /sdcard/OmniKali/ui && "
            f"uiautomator dump {UI_DUMP} >/dev/null 2>&1 && cat {UI_DUMP}"
        )
        return self._stdout(command)

    def _tap_label(self, label: str) -> bool:
        center = semantic_center(self._dump_ui(), label)
        if center is None:
            return False
        x, y = center
        self._run(f"input -d 0 tap {x} {y}")
        return True

    def _wait_label(self, label: str, attempts: int = 6, delay: float = 0.35) -> bool:
        for _ in range(attempts):
            if semantic_center(self._dump_ui(), label) is not None:
                return True
            self.sleep(delay)
        return False

    def _open_ruto_home(self) -> bool:
        self._run(f"am start -n {RUTO_ACTIVITY} >/dev/null 2>&1")
        for _ in range(4):
            self.sleep(0.35)
            if self._wait_label("Screens", attempts=1, delay=0):
                return True
            self._run("input -d 0 keyevent BACK")
        return self._wait_label("Screens", attempts=2)

    def _create_display(self) -> Optional[int]:
        before = {d.display_id for d in self._displays()}
        if not self._open_ruto_home() or not self._tap_label("Screens"):
            return None
        if not self._wait_label("Screen List") or not self._tap_label("Create Screen"):
            return None
        for _ in range(8):
            self.sleep(0.4)
            after = {d.display_id for d in self._displays()}
            new_ids = sorted(after - before)
            if new_ids:
                return new_ids[-1]
        return None

    def _open_display_detail(self, display_id: int) -> bool:
        if not self._open_ruto_home() or not self._tap_label("Screens"):
            return False
        if not self._wait_label("Screen List"):
            return False
        if not self._tap_label(f"#{display_id} {RUTO_DISPLAY_NAME}"):
            return False
        return self._wait_label("Select App")
    def _select_provider(self, display_id: int, package: str) -> bool:
        if not self._open_display_detail(display_id) or not self._tap_label("Select App"):
            return False
        if not self._wait_label("Search apps...") or not self._tap_label("Search apps..."):
            return False
        self._run(f"input -d 0 text {shlex.quote(package)}")
        self.sleep(0.5)
        center = semantic_center(self._dump_ui(), package)
        if center is None:
            return False
        x, y = center
        self._run(f"input -d 0 tap {x} {y}")
        return True

    def create(self, provider_id: str = "") -> SurfaceEvent:
        package = self._package(provider_id)
        self.provider_id = package
        probe = self._probe(package, self.display_id)
        if probe.healthy:
            self.display_id = probe.display_id
            self._attached = True
            return SurfaceEvent(True, "create", "ready", details=probe.as_dict())

        installed = self._stdout(f"pm path {shlex.quote(RUTO_PACKAGE)} 2>/dev/null || true")
        if not installed.strip():
            return SurfaceEvent(False, "create", "unavailable", "ruto_missing", "Ruto is not installed")
        display_id = self._create_display()
        if display_id is None:
            return SurfaceEvent(
                False, "create", "failed", "display_create_failed",
                "Ruto did not create a new virtual display",
            )
        self.display_id = display_id
        self.sleep(0.8)
        probe = self._probe(package, display_id)
        if not probe.healthy:
            if not self._select_provider(display_id, package):
                return SurfaceEvent(
                    False, "create", "failed", "app_attach_failed",
                    "Ruto display exists but provider app could not be selected",
                    {"display_id": display_id},
                )
            for _ in range(8):
                self.sleep(0.5)
                probe = self._probe(package, display_id)
                if probe.healthy:
                    break
        if not probe.healthy:
            return SurfaceEvent(
                False, "create", "stale", "evidence_incomplete",
                "Ruto launch did not satisfy all live-evidence checks",
                probe.as_dict(),
            )
        self._attached = True
        return SurfaceEvent(True, "create", "ready", details=probe.as_dict())

    def attach(self) -> SurfaceEvent:
        if not self.provider_id:
            return SurfaceEvent(False, "attach", "unknown", "provider_required", "create(provider_id) first")
        probe = self._probe(self.provider_id, self.display_id)
        if probe.healthy:
            self.display_id = probe.display_id
            self._attached = True
            return SurfaceEvent(True, "attach", "ready", details=probe.as_dict())
        return SurfaceEvent(
            False, "attach", "stale", "not_live",
            "provider is not live on a Ruto display", probe.as_dict(),
        )

    def inspect(self) -> SurfaceState:
        if not self.provider_id:
            return SurfaceState("ruto:unknown", False, False, "unknown", "")
        probe = self._probe(self.provider_id, self.display_id)
        if probe.healthy:
            self.display_id = probe.display_id
            self._attached = True
        state = "ready" if probe.healthy else ("stale" if probe.display else "unavailable")
        return SurfaceState(
            surface_id=f"ruto:{probe.display_id if probe.display_id is not None else 'none'}",
            attached=probe.healthy,
            focused=probe.healthy and self._focused,
            session=state,
            provider_id=self.provider_id,
            notes=[json.dumps(probe.as_dict(), sort_keys=True)],
        )

    def focus(self) -> SurfaceEvent:
        state = self.inspect()
        if not state.attached:
            return SurfaceEvent(False, "focus", state.session, "not_attached", "surface is not live")
        self._focused = True
        return SurfaceEvent(True, "focus", "ready", details={"display_id": self.display_id})

    def input(self, text: str) -> SurfaceEvent:
        if not self._focused or self.display_id is None:
            return SurfaceEvent(False, "input", "stale", "not_focused", "focus before input")
        if len(text) > 4096:
            return SurfaceEvent(False, "input", "failed", "too_long", "text exceeds 4096 characters")
        encoded = text.replace("%", "%25").replace(" ", "%s")
        self._run(f"input -d {self.display_id} text {shlex.quote(encoded)}")
        return SurfaceEvent(
            True, "input", "ready",
            details={"chars": len(text), "display_id": self.display_id},
        )
    def submit(self) -> SurfaceEvent:
        if not self._focused or self.display_id is None:
            return SurfaceEvent(False, "submit", "stale", "not_focused", "focus before submit")
        self._run(f"input -d {self.display_id} keyevent ENTER")
        return SurfaceEvent(True, "submit", "ready", details={"display_id": self.display_id})

    def observe(self) -> SurfaceEvent:
        state = self.inspect()
        return SurfaceEvent(
            state.attached, "observe", state.session,
            "ok" if state.attached else "not_live",
            details=state.as_dict(),
        )

    def recover(self) -> SurfaceEvent:
        if not self.provider_id:
            return SurfaceEvent(False, "recover", "unknown", "provider_required", "create(provider_id) first")
        return self.create(self.provider_id)

    def detach(self) -> SurfaceEvent:
        self._attached = False
        self._focused = False
        return SurfaceEvent(True, "detach", "ready", details={"display_id": self.display_id})

    def destroy(self) -> SurfaceEvent:
        return SurfaceEvent(
            False, "destroy", "ready", "unsupported",
            "display release requires a separately verified Ruto semantic action",
            {"display_id": self.display_id},
        )


VirtualSurface = RishSurface


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or ensure a Ruto-backed virtual surface")
    parser.add_argument("command", choices=("inspect", "ensure"))
    parser.add_argument("package")
    args = parser.parse_args()
    surface = RishSurface()
    surface.provider_id = surface._package(args.package)
    if args.command == "ensure":
        event = surface.create(args.package)
        print(json.dumps(event.as_dict(), sort_keys=True))
        return 0 if event.ok else 1
    state = surface.inspect()
    print(json.dumps(state.as_dict(), sort_keys=True))
    return 0 if state.attached else 1


if __name__ == "__main__":
    raise SystemExit(main())
