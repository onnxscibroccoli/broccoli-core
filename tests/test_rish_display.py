import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.surface.factory import open_surface
from tools.rish_display import (
    RishSurface,
    parse_ruto_displays,
    semantic_center,
    surface_on_display,
    task_on_display,
    window_on_display,
)


DISPLAY = """
    mBaseDisplayInfo=DisplayInfo{"Built-in Screen", displayId 0, FLAG_SECURE, owner android (uid 1000)}
    mBaseDisplayInfo=DisplayInfo{"Virtual Screen", displayId 30, displayGroupId 0, FLAG_PRIVATE, real 1080 x 2408, owner com.android.shell (uid 2000)}
    mBaseDisplayInfo=DisplayInfo{"Virtual Screen", displayId 31, displayGroupId 0, FLAG_PRIVATE, real 1080 x 2408, owner com.android.shell (uid 2000)}
"""
ACTIVITY = """
  displayId=30
      * Task{17a5d85 #1127 type=standard A=10298:com.example.provider}
        * ActivityRecord{b4a2fc u0 com.example.provider/.MainActivity t1127}
  displayId=31
      Application tokens in top down Z order:
"""
WINDOW = """
  Window #17 Window{90b2d44 u0 com.example.provider/com.example.provider.MainActivity}:
    mDisplayId=30 rootTaskId=1127
    mHasSurface=true isReadyForDisplay()=true
    Surface: shown=true      mDrawState=HAS_DRAWN
    isOnScreen=true
    isVisible=true
"""
SF = """
RequestedLayerState{com.example.provider/com.example.provider.MainActivity$_23569#29044 parentId=29043}
RequestedLayerState{Display 30 name="Virtual Screen"#28985 layerStack=30}
"""


class Result:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.ok = returncode == 0
        self.combined_output = stdout + stderr


class Backend:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def run(self, command):
        self.calls.append(command)
        for key, value in self.mapping:
            if key in command:
                return Result(value)
        return Result("")


class RishDisplayTests(unittest.TestCase):
    def test_parse_only_ruto_shell_virtual_displays(self):
        rows = parse_ruto_displays(DISPLAY)
        self.assertEqual([r.display_id for r in rows], [30, 31])
        self.assertTrue(all(r.private for r in rows))

    def test_live_evidence_parsers_agree(self):
        self.assertTrue(task_on_display(ACTIVITY, "com.example.provider", 30))
        self.assertFalse(task_on_display(ACTIVITY, "com.example.provider", 31))
        self.assertTrue(window_on_display(WINDOW, "com.example.provider", 30))
        self.assertTrue(surface_on_display(SF, "com.example.provider", 30))

    def test_semantic_center_uses_clickable_parent(self):
        xml = """<hierarchy>
        <node clickable="true" bounds="[42,694][1038,883]">
          <node text="Screens" content-desc="" clickable="false" bounds="[189,742][315,793]"/>
        </node>
        </hierarchy>"""
        self.assertEqual(semantic_center(xml, "Screens"), (540, 788))

    def test_create_display_confirms_default_dialog_before_polling(self):
        surface = RishSurface(backend=Backend([]), sleeper=lambda _: None)
        calls = []
        display_sets = [[], [30]]
        surface._displays = lambda: [
            type("D", (), {"display_id": x})() for x in display_sets.pop(0)
        ]
        surface._open_ruto_home = lambda: True
        surface._wait_label = lambda label, attempts=6, delay=0.35: calls.append(("wait", label)) or True
        surface._tap_label = lambda label: calls.append(("tap", label)) or True
        self.assertEqual(surface._create_display(), 30)
        self.assertEqual(
            calls,
            [
                ("tap", "Screens"),
                ("wait", "Screen List"),
                ("tap", "Create Screen"),
                ("wait", "Create New Display"),
                ("tap", "Create"),
            ],
        )

    def test_app_picker_uses_search_icon_before_search_field(self):
        surface = RishSurface(backend=Backend([]), sleeper=lambda _: None)
        labels = []
        surface._open_display_detail = lambda display_id: True
        surface._wait_label = lambda label, attempts=6, delay=0.35: labels.append(("wait", label)) or True
        surface._tap_label = lambda label: labels.append(("tap", label)) or True
        surface._run = lambda command: labels.append(("run", command)) or Result("")
        surface._dump_ui = lambda: (
            '<hierarchy><node clickable="true" bounds="[0,0][100,100]">'
            '<node text="com.example.provider" bounds="[10,10][90,90]"/>'
            '</node></hierarchy>'
        )
        self.assertTrue(surface._select_provider(30, "com.example.provider"))
        self.assertEqual(
            labels[:4],
            [
                ("tap", "Select App"),
                ("wait", "Search"),
                ("tap", "Search"),
                ("wait", "Search apps..."),
            ],
        )

    def test_probe_requires_all_live_evidence(self):
        backend = Backend([
            ("dumpsys display", DISPLAY),
            ("dumpsys activity", ACTIVITY),
            ("dumpsys window", WINDOW),
            ("SurfaceFlinger", SF),
            ("pidof", "23569\n"),
        ])
        surface = RishSurface(backend=backend, sleeper=lambda _: None)
        probe = surface._probe("com.example.provider")
        self.assertTrue(probe.healthy)
        self.assertEqual(probe.display_id, 30)

    def test_direct_display_launch_is_never_used(self):
        source = Path("tools/rish_display.py").read_text(encoding="utf-8")
        forbidden = "am start " + "--" + "display"
        self.assertNotIn(forbidden, source)
        self.assertNotIn("overlay" + "_display_devices", source)

    def test_invalid_package_fails_closed(self):
        surface = RishSurface(backend=Backend([]), sleeper=lambda _: None)
        with self.assertRaises(ValueError):
            surface.create("com.example;id")

    def test_factory_loads_rish_surface_on_android_without_silent_fallback(self):
        with patch("runtime.surface.factory._android_rish_available", return_value=True):
            surface, kind = open_surface()
        self.assertEqual(kind, "rish")
        self.assertEqual(type(surface).__name__, "RishSurface")


if __name__ == "__main__":
    unittest.main()
