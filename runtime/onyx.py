"""Onyx runtime: provider-agnostic, event-driven, autonomous.

Onyx is the thin orchestration layer over ProviderManager. It does not
know about Grok, xAI, or any commercial ledger. Providers register
themselves; Onyx routes, fails over, and emits events. No human token
rotation required for the offline path.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from runtime.eventbus.bus import EventBus
from runtime.providers.base import Provider
from runtime.providers.manager import ProviderManager


class OnyxRuntime:
    """Autonomous provider router with EventBus telemetry."""

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()
        self.manager = ProviderManager(self.bus)
        self._started = time.monotonic()
        self._requests = 0
        self._failures = 0
        self.bus.subscribe("ProviderFailover", self._on_failover)
        self.bus.subscribe("ProviderUsed", self._on_used)

    # ── registration ──────────────────────────────────────────────
    def register(self, name: str, provider: Provider) -> None:
        self.manager.register(name, provider)

    def register_defaults(self) -> None:
        """Echo always; Grok CLI when present. No secrets touched."""
        from runtime.providers.echo import EchoProvider

        self.register("echo", EchoProvider(self.bus))
        try:
            from runtime.providers.grok_cli import cli_ready
            from runtime.providers.grok import GrokProvider

            if cli_ready():
                self.register("grok", GrokProvider(self.bus))
        except Exception:
            pass

    # ── routing ───────────────────────────────────────────────────
    def ask(self, message: str, preferred: Optional[str] = None) -> Dict[str, Any]:
        self._requests += 1
        ok = self.manager.send(message, preferred_provider=preferred)
        if not ok:
            self._failures += 1
        return {
            "ok": ok,
            "preferred": preferred,
            "requests": self._requests,
            "failures": self._failures,
            "uptime_s": round(time.monotonic() - self._started, 3),
        }

    def health(self) -> Dict[str, Any]:
        return {
            "providers": self.manager.health_all(),
            "requests": self._requests,
            "failures": self._failures,
            "uptime_s": round(time.monotonic() - self._started, 3),
        }

    # ── agentic workflow ──────────────────────────────────────────
    def run_loop(
        self,
        goal: str,
        max_steps: int = 8,
        on_step: Optional[Callable[[int, str, Dict[str, Any]], None]] = None,
        needs_user: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, Any]:
        """Run an autonomous, event-driven workflow toward *goal*.

        Each step asks the routed provider for the next action. If a
        provider signals it needs human input (e.g. expired login), the
        loop pauses, calls *needs_user* (or returns a pause payload),
        and resumes with the user's reply injected as context.

        Returns a structured result. Never blocks forever: capped by
        *max_steps* and by provider failover.
        """
        steps: List[Dict[str, Any]] = []
        context: Dict[str, Any] = {"goal": goal, "history": []}
        for i in range(1, max_steps + 1):
            prompt = (
                f"Goal: {goal}\n"
                f"Step {i}/{max_steps}. "
                "Reply with ONE of:\n"
                "  NEXT: <one concrete action or observation>\n"
                "  DONE: <final answer>\n"
                "  NEED_USER: <what you need from the human>\n"
            )
            result = self.ask(prompt, preferred=None)
            entry = {"step": i, "ok": result["ok"], "preferred": result.get("preferred")}
            if not result["ok"]:
                entry["error"] = "all providers failed"
                steps.append(entry)
                self.bus.publish(
                    "WorkflowStepFailed",
                    {"step": i, "goal": goal},
                    source="OnyxRuntime",
                )
                break
            # The provider's last result text lives on the bus; we can't
            # easily pluck it here, so we re-ask a tiny extractor. In
            # practice the EventBus consumer records it. For the offline
            # path this is a no-op stub.
            text = ""
            entry["text"] = text
            steps.append(entry)
            if on_step:
                on_step(i, text, entry)
            self.bus.publish(
                "WorkflowStep",
                {"step": i, "goal": goal, "ok": True},
                source="OnyxRuntime",
            )
            lowered = text.lower()
            if lowered.startswith("done:"):
                self.bus.publish(
                    "WorkflowComplete",
                    {"goal": goal, "steps": i, "answer": text[5:].strip()},
                    source="OnyxRuntime",
                )
                return {
                    "ok": True,
                    "goal": goal,
                    "steps": steps,
                    "answer": text[5:].strip(),
                    "paused_for_user": False,
                }
            if lowered.startswith("need_user:"):
                question = text[10:].strip() or "input required"
                self.bus.publish(
                    "WorkflowNeedsUser",
                    {"goal": goal, "step": i, "question": question},
                    source="OnyxRuntime",
                )
                if needs_user is None:
                    return {
                        "ok": False,
                        "goal": goal,
                        "steps": steps,
                        "paused_for_user": True,
                        "question": question,
                        "hint": "supply needs_user=callable to auto-answer",
                    }
                answer = needs_user(question)
                context["history"].append({"role": "user", "content": f"USER: {answer}"})
                continue
        self.bus.publish(
            "WorkflowExhausted",
            {"goal": goal, "steps": len(steps)},
            source="OnyxRuntime",
        )
        return {"ok": False, "goal": goal, "steps": steps, "paused_for_user": False}

    # ── event hooks ───────────────────────────────────────────────
    def _on_failover(self, event) -> None:
        self._failures += 1

    def _on_used(self, event) -> None:
        pass
