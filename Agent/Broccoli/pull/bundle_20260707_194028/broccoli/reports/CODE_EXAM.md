# CODE_EXAM (device)

## broccoli/tools/broccoli_brain.py
```
lines=89 bytes=3038 flags=pkg_com.ai.x.grok,pkg_ai.x.grok,brocc,rish

#!/usr/bin/env python3
"""
Single entry: rish (foreground) + brocc (send|ask) + queue drain.
WIRE_MODE=send|ask  (ask = your working brocc ask + poll path)
"""
import json, subprocess, sys, time, shutil
from pathlib import Path

B = Path.home() / "broccoli"
ENV = B / "meta/wire_coords.env"
LOG = B / "reports/agent_loop.log"
Q = B / "queue/agent_task.txt"

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {m}\n")

def load_env():
    o = {"GROK_PKG": "com.ai.x.grok", "WIRE_MODE": "ask", "COLLAB_POLL_SEC": "0"}
    if ENV.is_file():
        for line in ENV.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                o[k.strip()] = v.strip()
    return o

def rish(cmd, t=60):
    return subprocess.run(["rish", "-c", cmd], capture_output=True, text=True, timeout=t)

def has_brocc():
    return shutil.which("brocc") is not None

def foreground_grok(pkg):
    log(f"STEP foreground_grok pkg={pkg}")
    if has_brocc():
        subprocess.run(["brocc", "launch-grok"], capture_output=True, text=True, timeout=90)
        time.sleep(1.0)
    rish(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {pkg}")
    time.sleep(0.7)
    log("OK foreground_rish_am_start")

def wire(msg, cfg):
    pkg = cfg.get("GROK_PKG", "com.ai.x.grok")
    if pkg == "ai.x.grok":
        pkg = "com.ai.x.grok"
        log("WARN fixed pkg ai.x.grok -> com.ai.x.grok")
    foreground_grok(pkg)
    mode = cfg.get("WIRE_MODE", "ask")
    if not has_brocc():
        log("FAIL no_brocc")
        return 1
    log(f"TRY brocc_{mode} len={len(msg)}")
    if mode == "ask":
        r = subprocess.run(["brocc", "ask", msg], capture_output=True, text=True, timeout=300)
    else:
        r = subprocess.run(["brocc", "send", msg], capture_output=True, text=True, timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    log(f"brocc rc={r.returncode} tail={out[-200:].replace(chr(10), ' ')}")
    if "OK sent" in out or "BROCCOLI_DONE" in out or (r.returncode == 0 and "FAIL" not in out[-80:]):
        log("OK wire_brocc")
        return 0
    log("FAIL wire_brocc")
    return 1

def drain():
    if not Q.is_file() or Q.stat().st_size == 0:
        return
    msg = Q.read_text(encoding="utf-8", errors="replace")[:3800]
    log(f"TRY queue_bytes={len(msg)}")
    if wire(msg, load_env()) == 0:
        Q.write_text("")
        log("OK queue_cleared")

def loop():
    log("OK broccoli_brain started WIRE_MODE=" + load_env().get("WIRE_MODE", "ask"))
    while True:
        drain()
        time.sleep(float(load_env().get("COLLAB_POLL_SEC", "0") or 0))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        drain()
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "send":
        sys.exit(wire(" ".join(sys.argv[2:]), load_env()))
    loop()

```

## broccoli/tools/ui_dump_loop.py
```
lines=133 bytes=5031 flags=pkg_com.ai.x.grok,pkg_ai.x.grok,brocc,rish
... truncated (13 more lines)

#!/usr/bin/env python3
"""Optimized UI dump loop: foreground gate, hash skip, snapshot for Mac/Grok agent."""
import hashlib, json, re, subprocess, sys, time, shutil
from pathlib import Path
from xml.etree import ElementTree as ET

B = Path.home() / "broccoli"
ENV = B / "meta/dump_loop.env"
XML = B / "reports/ui_dump.xml"
CTX = B / "reports/wire_context.json"
SNAP = B / "reports/ui_snapshot.json"
LOG = B / "reports/ui_dump_loop.log"
Q = B / "queue/agent_task.txt"
LAST_HASH = B / "reports/.ui_dump_hash"

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {m}\n")

def cfg():
    o = {"GROK_PKG": "com.ai.x.grok", "DUMP_INTERVAL_SEC": "3", "DUMP_INTERVAL_IDLE_SEC": "10",
         "DUMP_ONLY_IF_FOREGROUND": "1", "SKIP_IF_XML_UNCHANGED": "1"}
    if ENV.is_file():
        for line in ENV.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                o[k.strip()] = v.strip()
    return o

def rish(c, t=45):
    return subprocess.run(["rish", "-c", c], capture_output=True, text=True, timeout=t)

def sync_dump():
    if shutil.which("brocc"):
        subprocess.run(["brocc", "dump"], capture_output=True, text=True, timeout=90)
    if not XML.is_file() or XML.stat().st_size < 500:
        rish("uiautomator dump /data/local/tmp/broccoli_ui.xml")
        r = rish("cat /data/local/tmp/broccoli_ui.xml")
        if r.stdout and len(r.stdout) > 500:
            XML.write_text(r.stdout, encoding="utf-8", errors="replace")
    return XML.is_file() and XML.stat().st_size > 500

def parse_context(raw: str) -> dict:
    composer = send = None
    pkg = ""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return {"package": "", "composer": None, "send": None}
    def nums(s):
        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", s or "")
        return tuple(map(int, m.groups())) if m else None
    def area(b):
        return (b[2]-b[0])*(b[3]-b[1]) if b else 0
    sends = []
    for n in root.iter():
        pkg = n.attrib.get("package") or pkg
        cls = n.attrib.get("class") or ""
        b = nums(n.attrib.get("bounds"))
        if not b:
            continue
        if "EditText" in cls:
            if composer is None or area(b) > area(composer["bounds"]):
                composer = {"text": (n.attrib.get("text") or "")[:500], "bounds": list(b)}
        lab = (n.attrib.get("content-desc") or n.attrib.get("text") or "").strip()
        if re.search(r"(?i)send|submit", lab):
            sends.append({"label": lab, "bounds": list(b)})
    if sends:
        send = sends[-1]
    return {"package": pkg, "composer": composer, "send": send}

def grok_foreground(raw: str, pkg: str) -> bool:
    return pkg in raw or "grok" in raw.lower() or "com.ai.x.grok" in raw

def snapshot(ctx: dict, queue_bytes: int, changed: bool):
    snap = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queue_bytes": queue_bytes,
        "dump_changed": changed,
        "foreground_grok": grok_foreground(XML.read_text(errors="replace"), ctx.get("package", "")),
        "wire_context": ctx,
    }
    SNAP.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    CTX.write_text(json.dumps(ctx, indent=0), encoding="utf-8")

def content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]

def tick(force=False):
    c = cfg()
    pkg = c.get("GROK_PKG", "com.ai.x.grok")
    qbytes = Q.stat().st_size if Q.is_file() else 0
    if not sync_dump():
        log("SKIP dump_fail")
        return
    raw = XML.read_text(errors="replace")
    if c.get("DUMP_ONLY_IF_FOREGROUND", "1") == "1" and not grok_foreground(raw, pkg):
        log("SKIP not_foreground")
        return
    h = content_hash(raw)
    prev = LAST_HASH.read_text().strip() if LAST_HASH.is_file() else ""
    changed = h != prev
    if c.get("SKIP_IF_XML_UNCHANGED", "1") == "1" and not changed and not force:
        log("SKIP unchanged")
        return
    LAST_HASH.write_text(h)
    ctx = parse_context(raw)
    snapshot(ctx, qbytes, changed)
    log(f"OK dump composer={bool(ctx.get('composer'))} send={bool(ctx.get('send'))} q={qbytes} changed={changed}")

def loop():
    log("OK ui_dump_loop started")
    last_q = -1
    while True:
        c = cfg()
        qbytes = Q.stat().st_size if Q.is_file() else 0
        if c.get("DUMP_ON_QUEUE_CHANGE", "1") == "1" and qbytes != last_q and qbytes > 0:

```

## broccoli/tools/pull_wire_from_dump.py
```
MISSING: /data/data/com.termux/files/home/broccoli/tools/pull_wire_from_dump.py

```

## broccoli/tools/broccoli_supervisor.sh
```
lines=12 bytes=533 flags=termux
#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH"
L="$HOME/broccoli/reports/supervisor.log"
log(){ echo "$(date -Iseconds) $*" >>"$L"; }
if ! pgrep -f "broccoli/tools/broccoli_brain.py" >/dev/null; then
  nohup python3 "$HOME/broccoli/tools/broccoli_brain.py" >>"$HOME/broccoli/reports/daemon.log" 2>&1 &
  log START brain
fi
if ! pgrep -f "broccoli/tools/ui_dump_loop.py" >/dev/null; then
  nohup python3 "$HOME/broccoli/tools/ui_dump_loop.py" >>"$HOME/broccoli/reports/daemon.log" 2>&1 &
  log START dump
fi

```

## broccoli/meta/wire_coords.env
```
lines=5 bytes=93 flags=pkg_com.ai.x.grok,pkg_ai.x.grok
GROK_PKG=com.ai.x.grok
WIRE_MODE=ask
COLLAB_POLL_SEC=0
TYPING_IDLE_SEC=1
WIRE_COOLDOWN_SEC=0

```

## broccoli/reports/wire_context.json
```
lines=5 bytes=49 flags=-
{
"package": "",
"composer": null,
"send": null
}

```

## broccoli/inbox/google/1783310243_research.txt
```
lines=4 bytes=272 flags=shizuku,termux
Research concisely with sources cited:
Use Google AI Mode on this phone to research: Android UI automation patterns (Shizuku, Termux, accessibility).
Each OK answer: worker merges reply into ~/broccoli/research/notes.md.
Grok jobs only for NEXT_STEP and patching Broccoli.

```

## broccoli/inbox/grok/1783309612.txt
```
lines=1 bytes=114 flags=-
Read tasks/current/TASK.md. One NEXT_STEP + TERMINUX + TEST. If all acceptance met, say TASK_COMPLETE: <summary>.

```

## bin/brocc
```
MISSING: /data/data/com.termux/files/home/bin/brocc

```

## project_mythara/app/src/main/kotlin/com/mythara/agent/tools/TermuxExecTool.kt
```
lines=374 bytes=18686 flags=rwa,termux
... truncated (254 more lines)
package com.mythara.agent.tools

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.core.content.ContextCompat
import com.mythara.agent.Tool
import com.mythara.agent.ToolResult
import com.mythara.services.TermuxAvailability
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/**
 * `termux_exec` — run a shell command inside Termux's Debian-grade
 * userland via the `com.termux.RUN_COMMAND` intent.
 *
 * Why this exists when `run_shell` already does shell:
 *   - `run_shell` runs inside Mythara's app sandbox — toybox + GNU
 *     subset, no `apt`, no persistent `$HOME`, no `~/.bashrc`, no
 *     real TTY.
 *   - Termux ships a full GNU userland with `pkg install`, `git`,
 *     `python`, `node`, `npm`, `ssh`, `vim`, etc. Long-lived `$HOME`
 *     in `/data/data/com.termux/files/home`. The agent can run any
 *     of it through one intent dispatch.
 *
 * Result delivery: Termux returns the exec result via a `PendingIntent`
 * we ship with the request. We register a one-shot `BroadcastReceiver`
 * bound to a UUID-suffixed action, suspend on a [CompletableDeferred],
 * and resolve when Termux fires the PI. The receiver is unregistered
 * in `finally` to keep the process tidy.
 *
 * Failure modes:
 *   - Termux not installed → returns `{status:"not_installed", hint:…}`
 *     (no exception thrown so the agent can recover and fall back to
 *     `run_shell`).
 *   - `allow-external-apps=true` not set in `~/.termux/termux.properties`
 *     → Termux drops the request silently; we time out and return
 *     `{status:"timeout", hint:"check allow-external-apps"}`.
 *   - Command exits non-zero → returns `{status:"ok", exitCode:N, …}`
 *     (non-zero exit is data, not an error — same as `run_shell`).
 */
@Singleton
class TermuxExecTool @Inject constructor(
    @ApplicationContext private val context: Context,
    private val availability: TermuxAvailability,
) : Tool {
    override val name = "termux_exec"
    override val description =
        "DEFAULT shell tool when Termux is installed. Runs ONE binary inside Termux's full " +
            "GNU/Linux userland with persistent \$HOME and apt-installable packages. " +
            "`command` is JUST a binary name (e.g. \"curl\", \"git\", \"python\") — NEVER a " +
            "shell pipeline. For pipelines / && chains / \$VAR expansion, use command=\"sh\" " +
            "with args=[\"-c\",\"<full pipeline as one string>\"]. Examples: " +
            "(curl -sI URL) → {command:\"curl\", args:[\"-sI\",\"URL\"]}; " +
            "(curl URL | jq .x) → {command:\"sh\", args:[\"-c\",\"curl URL | jq .x\"]}. " +
            "Returns {status:\"ok\", exitCode, stdout, stderr}; falls back to structured error " +
            "when Termux isn't installed."

    override val parameters = buildJsonObject {
        put("type", "object")
        put("properties", buildJsonObject {
            put("command", buildJsonObject {
                put("type", "string")
                put(
                    "description",
                    "ONE binary to run — JUST the binary name or path. NEVER a shell pipeline. " +
                        "Bare names (e.g. 'curl', 'git', 'python') resolve against " +
                        "/data/data/com.termux/files/usr/bin/. Absolute paths used as-is. " +
                        "If you need pipes, redirection, &&, ||, or \$VAR expansion, set " +
                        "command='sh' and put the WHOLE pipeline as ONE string in args[1] " +
                        "after args[0]='-c'.",
                )
            })
            put("args", buildJsonObject {
                put("type", "array")
                put(
                    "description",
                    "Arguments to the binary, each as a separate string. For sh -c pipelines, " +
                        "use exactly two args: ['-c', 'the full pipeline as one string']. " +
                        "Example: ['-c', 'curl -s https://api.example.com | jq .field'].",
                )
                put("items", buildJsonObject { put("type", "string") })
            })
            put("workdir", buildJsonObject {
                put("type", "string")
                put(
                    "description",
                    "Working directory inside Termux. Default Termux \$HOME " +
                        "(/data/data/com.termux/files/home).",
                )
            })
            put("background", buildJsonObject {
                put("type", "boolean")
                put(
                    "description",
                    "true = run silently via RunCommandService (default; result returned " +
                        "via callback). false = run in Termux's foreground session (TTY mode; " +
                        "user sees the command). Use false for `vim`, `htop`, interactive REPLs.",
                )
            })
            put("timeout_ms", buildJsonObject {

```

## project_mythara/app/src/main/kotlin/com/mythara/agent/tools/AutomationTools.kt
```
lines=180 bytes=8428 flags=-
... truncated (60 more lines)
package com.mythara.agent.tools

import com.mythara.agent.ConfirmationGate
import com.mythara.agent.Tool
import com.mythara.agent.ToolResult
import com.mythara.services.PhoneControlAccessibilityService
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import javax.inject.Inject
import javax.inject.Singleton

/**
 * M6 automation tools. Each one drives the device via
 * [PhoneControlAccessibilityService]'s gesture dispatch + node
 * actions. All three require user confirmation through
 * [ConfirmationGate] — they perform actions on the user's behalf
 * inside other apps, which is exactly the surface that needs an
 * explicit "yes" before each call.
 *
 * Coordinates are absolute screen pixels. The model gets dimensions
 * from `read_screen` if it needs to pick a target visually. We don't
 * try to translate "tap the Send button" into coords here — that's
 * the model's job once it sees the screen snapshot.
 */

@Singleton
class TapTool @Inject constructor() : Tool {

    override val name: String = "tap"
    override val description: String =
        "Tap a single point on the screen at (x,y) screen pixels. " +
            "Use after read_screen to interact with a UI element the model identified. " +
            "Requires the user to grant Accessibility access and confirm each tap."

    override val requiresConfirmation: Boolean = true

    override val parameters: JsonObject = buildJsonObject {
        put("type", "object")
        put(
            "properties",
            buildJsonObject {
                put("x", buildJsonObject { put("type", "integer"); put("description", "Horizontal screen pixel.") })
                put("y", buildJsonObject { put("type", "integer"); put("description", "Vertical screen pixel.") })
            },
        )
        put("required", JsonArray(listOf(JsonPrimitive("x"), JsonPrimitive("y"))))
    }

    override fun confirmationFor(args: JsonObject): ConfirmationGate.ConfirmRequest {
        val x = (args["x"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 0
        val y = (args["y"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 0
        // No allowlist key — each tap is a unique location, blanket
        // grants would defeat the point. Users who want hands-off
        // automation can flip a future "automation mode" master toggle.
        return ConfirmationGate.ConfirmRequest(
            id = "", toolName = name,
            title = "Tap screen at ($x, $y)?",
            body = "Mythara wants to dispatch a tap gesture at this point on whatever's currently on screen.",
        )
    }

    override suspend fun execute(args: JsonObject): ToolResult {
        val service = PhoneControlAccessibilityService.instance
            ?: return ToolResult(false, """{"error":"accessibility_not_granted","detail":"Enable Mythara in Settings → Accessibility."}""")
        val x = (args["x"] as? JsonPrimitive)?.content?.toIntOrNull()
            ?: return ToolResult(false, """{"error":"missing_x"}""")
        val y = (args["y"] as? JsonPrimitive)?.content?.toIntOrNull()
            ?: return ToolResult(false, """{"error":"missing_y"}""")
        val ok = service.tap(x.toFloat(), y.toFloat())
        return if (ok) ToolResult(true, """{"ok":true,"x":$x,"y":$y}""")
        else ToolResult(false, """{"error":"gesture_failed","detail":"Accessibility service rejected or canceled the tap. Coordinates may be off-screen."}""")
    }
}

@Singleton
class SwipeTool @Inject constructor() : Tool {

    override val name: String = "swipe"
    override val description: String =
        "Swipe from (x1,y1) to (x2,y2) over an optional duration. " +
            "Use to scroll, drag, or fling. Defaults to 300ms which feels like a natural scroll."

    override val requiresConfirmation: Boolean = true

    override val parameters: JsonObject = buildJsonObject {
        put("type", "object")
        put(
            "properties",
            buildJsonObject {
                put("x1", buildJsonObject { put("type", "integer") })
                put("y1", buildJsonObject { put("type", "integer") })
                put("x2", buildJsonObject { put("type", "integer") })
                put("y2", buildJsonObject { put("type", "integer") })
                put(
                    "duration_ms",
                    buildJsonObject {
                        put("type", "integer")
                        put("description", "Optional, default 300, range 50-2000.")
                    },
                )
            },
        )
        put("required", JsonArray(listOf("x1", "y1", "x2", "y2").map { JsonPrimitive(it) }))
    }

    override fun confirmationFor(args: JsonObject): ConfirmationGate.ConfirmRequest {
        val x1 = (args["x1"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 0
        val y1 = (args["y1"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 0
        val x2 = (args["x2"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 0
        val y2 = (args["y2"] as? JsonPrimitive)?.content?.toIntOrNull() ?: 0
        return ConfirmationGate.ConfirmRequest(
            id = "", toolName = name,
            title = "Swipe from ($x1, $y1) to ($x2, $y2)?",
            body = "Mythara wants to drag/fling across the screen on the foreground app.",
        )
    }


```

## project_mythara/app/src/main/kotlin/com/mythara/agent/tools/ReadScreenTool.kt
```
lines=66 bytes=2750 flags=-
package com.mythara.agent.tools

import com.mythara.agent.Tool
import com.mythara.agent.ToolResult
import com.mythara.services.PhoneControlAccessibilityService
import com.mythara.services.ScreenReader
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import javax.inject.Inject
import javax.inject.Singleton

/**
 * `read_screen` — returns a compact JSON snapshot of the currently
 * foregrounded app's UI. Powered by [PhoneControlAccessibilityService]
 * and [ScreenReader].
 *
 * Failure modes the model needs to understand:
 *   - service not granted (user never enabled it in
 *     Settings → Accessibility) → `error: accessibility_not_granted`
 *   - no active window (rare; usually transient between activities)
 *     → `error: no_active_window`
 *
 * Read-only — never confirmed before execution. Confirmation gating
 * is reserved for the M6 automation tools (tap / swipe / type) and
 * the M7 communication tools (SMS / call) that actually do things on
 * the user's behalf.
 */
@Singleton
class ReadScreenTool @Inject constructor(
    private val screenReader: ScreenReader,
) : Tool {

    override val name: String = "read_screen"

    override val description: String =
        "Read the user's current phone screen and return a structured JSON snapshot of what's visible (text, buttons, fields, scroll containers). Use when the user asks 'what's on my screen' or you need to understand the foreground app's UI to answer."

    override val parameters: JsonObject = buildJsonObject {
        put("type", "object")
        put("properties", buildJsonObject {})
        put("required", kotlinx.serialization.json.JsonArray(emptyList()))
    }

    override suspend fun execute(args: JsonObject): ToolResult {
        val service = PhoneControlAccessibilityService.instance
            ?: return ToolResult(
                ok = false,
                output = """{"error":"accessibility_not_granted","detail":"Mythara's Accessibility Service isn't enabled. Open Settings → Accessibility → Mythara to grant it."}""",
            )
        val root = service.currentRootNode()
        if (root == null) {
            return ToolResult(
                ok = false,
                output = """{"error":"no_active_window","detail":"Nothing in the foreground or the system briefly blocked us. Try again."}""",
            )
        }
        val snapshot = screenReader.snapshot(root)
            ?: return ToolResult(
                ok = false,
                output = """{"error":"snapshot_failed"}""",
            )
        runCatching { root.recycle() }
        return ToolResult(ok = true, output = screenReader.render(snapshot))
    }
}

```

## project_mythara/app/src/main/kotlin/com/mythara/services/ShizukuService.kt
```
lines=153 bytes=6040 flags=shizuku
... truncated (33 more lines)
package com.mythara.services

import android.content.pm.PackageManager
import android.util.Log
import kotlinx.coroutines.suspendCancellableCoroutine
import rikka.shizuku.Shizuku
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume

/**
 * Singleton wrapper around the Shizuku API.
 *
 * Shizuku ([https://shizuku.rikka.app/]) is a free, open-source shim
 * that gives ordinary apps access to a small set of system APIs
 * normally gated by signature- or system-protected permissions
 * (notably `WRITE_SECURE_SETTINGS`, parts of `IPackageManager`,
 * etc.). The user installs the Shizuku app from Play, bootstraps it
 * once via adb / wireless debugging, and apps that declare
 * Shizuku support can then make IPC calls into the shell-uid
 * Shizuku process to run those operations.
 *
 * For Mythara, we use Shizuku exclusively for the cosmetic-tweak
 * pipeline ([com.mythara.agent.tools.CosmeticTool]) so the agent can
 * apply non-invasive system changes (font scale, dark mode, accent
 * color, gesture-nav mode) without ever asking for root or modifying
 * `/system`.
 *
 * State semantics:
 *
 *   - [State.NotInstalled] — the Shizuku app isn't on the device.
 *     Cosmetic tool returns setup-card #1 (install steps).
 *   - [State.NotRunning] — installed but the Shizuku process isn't
 *     live. Setup-card #2 (start steps).
 *   - [State.PermissionDenied] — running, but the user hasn't
 *     granted Mythara access yet. Setup-card #3 (grant steps).
 *   - [State.Ready] — green light. Cosmetic operations proceed.
 */
@Singleton
class ShizukuService @Inject constructor() {

    enum class State {
        NotInstalled,
        NotRunning,
        PermissionDenied,
        Ready,
    }

    /** Snapshot the current Shizuku state. Cheap — no blocking IPC. */
    fun state(packageManager: PackageManager): State {
        val installed = isInstalled(packageManager)
        if (!installed) return State.NotInstalled
        val running = try {
            Shizuku.pingBinder()
        } catch (_: Throwable) {
            false
        }
        if (!running) return State.NotRunning
        val granted = try {
            Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        } catch (_: Throwable) {
            false
        }
        return if (granted) State.Ready else State.PermissionDenied
    }

    /** Whether the Shizuku app is installed on the device. */
    private fun isInstalled(pm: PackageManager): Boolean = try {
        pm.getPackageInfo("moe.shizuku.privileged.api", 0)
        true
    } catch (_: PackageManager.NameNotFoundException) {
        false
    }

    /** Request Shizuku permission. Resumes with the granted state.
     *  No-op if not running. */
    suspend fun requestPermission(): Boolean = suspendCancellableCoroutine { cont ->
        try {
            if (!Shizuku.pingBinder()) {
                cont.resume(false)
                return@suspendCancellableCoroutine
            }
            if (Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
                cont.resume(true)
                return@suspendCancellableCoroutine
            }
            val listener = object : Shizuku.OnRequestPermissionResultListener {
                override fun onRequestPermissionResult(requestCode: Int, grantResult: Int) {
                    if (requestCode != REQ_CODE) return
                    Shizuku.removeRequestPermissionResultListener(this)
                    cont.resume(grantResult == PackageManager.PERMISSION_GRANTED)
                }
            }
            Shizuku.addRequestPermissionResultListener(listener)
            cont.invokeOnCancellation {
                Shizuku.removeRequestPermissionResultListener(listener)
            }
            Shizuku.requestPermission(REQ_CODE)
        } catch (t: Throwable) {
            Log.w(TAG, "requestPermission failed: ${t.message}")
            cont.resume(false)
        }
    }

    /**
     * Execute a command through Shizuku's process (which runs with
     * shell UID, so it can `settings put`, etc.).
     *
     * Shizuku's `newProcess` method is marked `@hide` (so not on the
     * Kotlin-callable public surface), but it IS the documented path
     * for ad-hoc shell exec — the official sample uses it via Java
     * reflection. We do the same: reflect into the method, invoke
     * with the command split into `sh -c <command>`. If the method
     * shape changes in a future Shizuku release the call fails and
     * we return null, the CosmeticTool degrades gracefully.
     *
     * Returns the merged stdout+stderr as a String, or null if the
     * Shizuku process refused / errored.
     */
    fun execShell(command: String): ShellResult? {

```

## project_mythara/app/src/main/kotlin/com/mythara/minimax/GeminiVisionService.kt
```
lines=293 bytes=11760 flags=gemini
... truncated (173 more lines)
package com.mythara.minimax

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Gemini vision backend. An optional alternative to MiniMax-VL-01 for
 * the `take_photo` tool's image-analysis pass.
 *
 * Why a separate service:
 *  - Gemini's wire format is its own thing (REST `:generateContent`,
 *    not the OpenAI-compatible `chat/completions`). Trying to share
 *    DTOs with the MiniMax path means polymorphism we don't need.
 *  - The auth model is different — query-param `?key=…` rather than
 *    a Bearer header.
 *  - Endpoint is fixed to `generativelanguage.googleapis.com`; there
 *    is no region toggle.
 *
 * The key itself is encrypted at rest via Tink in [SettingsStore]
 * exactly like the MiniMax key — same Keystore wrapping. The user
 * provides it through a separate Settings panel.
 *
 * Free tier note: Gemini API offers a generous free tier for personal
 * projects (rate-limited per-minute / per-day). The user creates a
 * key at https://aistudio.google.com/app/apikey and pastes it in.
 */
@Singleton
class GeminiVisionService @Inject constructor() {

    data class Outcome(val ok: Boolean, val text: String, val code: String? = null)

    private val http: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = false; explicitNulls = false }

    suspend fun describeImage(
        imageFile: File,
        prompt: String,
        apiKey: String,
        model: String = DEFAULT_MODEL,
    ): Outcome = withContext(Dispatchers.IO) {
        if (apiKey.isBlank()) {
            return@withContext Outcome(false, "Gemini API key not set.", "missing_api_key")
        }
        if (!imageFile.exists() || imageFile.length() == 0L) {
            return@withContext Outcome(false, "Image file missing or empty.", "no_image")
        }
        // Downsample on decode + re-encode as JPEG so what we send
        // Gemini is bounded. Without this, every modern phone photo
        // (~8 MB raw JPEG) crashed the request against the size cap
        // and the bulk re-caption walker silently fell through to
        // MiniMax-VL — which usually didn't have a key either, so
        // the row was marked FAILED. Same pattern GemmaVisionService
        // already uses; we mirror it here so the cloud path enjoys
        // the same headroom.
        val bytes = runCatching { downsampleToJpeg(imageFile) }.getOrElse {
            return@withContext Outcome(false, "Couldn't decode image: ${it.message}", "decode_failed")
        } ?: return@withContext Outcome(false, "Couldn't decode image (null bitmap).", "decode_failed")
        if (bytes.size > MAX_BYTES) {
            // After downsampling, this should never trigger for a
            // normal phone photo — but keep the guard as belt-and-
            // suspenders for pathological inputs (panoramas etc.).
            return@withContext Outcome(
                false,
                "Image too large after downsample (${bytes.size} bytes), capped at $MAX_BYTES.",
                "image_too_large",
            )
        }
        Log.v(TAG, "downsampled ${imageFile.length()}B → ${bytes.size}B for Gemini")
        val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
        val body = GenerateContentRequest(
            contents = listOf(
                GeminiContent(
                    parts = listOf(
                        GeminiPart(text = prompt),
                        GeminiPart(
                            inlineData = GeminiInlineData(mimeType = "image/jpeg", data = b64),
                        ),
                    ),
                ),
            ),
            generationConfig = GenerationConfig(
                temperature = 0.4,
                maxOutputTokens = MAX_RESPONSE_TOKENS,
            ),
        )
        val bodyJson = runCatching { json.encodeToString(GenerateContentRequest.serializer(), body) }
            .getOrElse {
                return@withContext Outcome(false, "Couldn't serialise request: ${it.message}", "serialise")
            }

        val url = "$BASE_URL/v1beta/models/$model:generateContent?key=$apiKey"
        val req = Request.Builder()
            .url(url)
            .post(bodyJson.toRequestBody("application/json".toMediaType()))
            .build()

        val result = runCatching { http.newCall(req).execute() }
        if (result.isFailure) {

```

## mantra/mantra.py
```
lines=89 bytes=2830 flags=-
#!/usr/bin/env python3
import numpy as np
import plotext as plt
import threading, time
from queue import Queue

class ONNXNode:
    def __init__(self):
        self.phase_space = []
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.running = True

    def ingest_signal(self, signal):
        self.input_queue.put(signal)

    def process_signal(self, signal):
        return np.array([signal['amplitude'], signal['phase'], signal['jitter']], dtype=np.float32)

    def run_node(self):
        while self.running:
            if not self.input_queue.empty():
                signal = self.input_queue.get()
                vector = self.process_signal(signal)
                self.phase_space.append(vector)
                self.output_queue.put(vector)
            else:
                time.sleep(0.05)

    def stop(self): self.running = False

class DistributedNetwork:
    def __init__(self, num_nodes=2):
        self.nodes = [ONNXNode() for _ in range(num_nodes)]

    def start_network(self):
        for node in self.nodes:
            threading.Thread(target=node.run_node, daemon=True).start()

    def broadcast_signal(self, signal):
        for node in self.nodes:
            node.ingest_signal(signal)

    def aggregate(self):
        aggregated = []
        for node in self.nodes:
            while not node.output_queue.empty():
                aggregated.append(node.output_queue.get())
        if aggregated:
            return np.mean(aggregated, axis=0)
        return None

    def self_nurture(self):
        for node in self.nodes:
            if node.phase_space:
                node.phase_space[-1] *= np.random.uniform(0.99,1.01,size=node.phase_space[-1].shape)

class FractalVisualizer:
    def __init__(self, network):
        self.network = network

    def run(self):
        try:
            while True:
                data = self.network.aggregate()
                if data is not None:
                    plt.clt()
                    plt.scatter([data[0]],[data[1]])
                    plt.plotsize(40,20)
                    plt.show()
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    network = DistributedNetwork()
    network.start_network()
    visualizer = FractalVisualizer(network)
    threading.Thread(target=visualizer.run, daemon=True).start()
    try:
        while True:
            simulated_signal = {"amplitude":np.random.rand(), "phase":np.random.rand()*2*np.pi, "jitter":np.random.rand()*0.01}
            network.broadcast_signal(simulated_signal)
            network.self_nurture()
            time.sleep(0.1)
    except KeyboardInterrupt:
        for node in network.nodes:
            node.stop()
        print("Quantum Hum Propagation Mantra terminated gracefully.")

```

## tasks/chrome-puppy/automation.md
```
lines=25 bytes=864 flags=rish
---
max_wait_sec: 90
slug: chrome-puppy
---

## Bootstrap
rish -c 'am start -a android.intent.action.VIEW -d "https://www.google.com/search?q=brown+puppy+pictures&tbm=isch" com.android.chrome'
wait: udm=2|tbm=isch|APjFqb 22
rish -c 'input swipe 540 1900 540 950 400'
wait: puppy|Brown|Shutterstock|iStock 8
rish -c 'input swipe 540 1900 540 950 400'
wait: puppy|Brown 6

## Goal
Open one brown puppy image in Chrome Images and save a real file to Downloads.

## Success signals
New image file under /sdcard/Download OR UI toast saved/download complete (not page title "Download Free Images").

## AI rounds
Bootstrap opened Images grid. Tap a thumbnail (coords from CURRENT_UI). Then Download / long-press Save image / menu Save.
After save, do not claim success until Downloads has a new file.

## Constraints
rish -c and sleep only in AI COMMANDS. Max 10 lines.

```
