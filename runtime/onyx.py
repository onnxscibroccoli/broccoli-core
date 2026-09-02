"""Onyx: provider-agnostic loop. Echo is the constitution. Cloud is optional."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class OnyxRuntime:
    def __init__(self, bus=None) -> None:
        self.bus = bus
        self._providers: Dict[str, Any] = {}
        self._order: List[str] = []
        self._failures = 0

    def register(self, name: str, provider: Any) -> None:
        self._providers[name] = provider
        if name not in self._order:
            self._order.append(name)
        if hasattr(provider, "initialize"):
            try:
                provider.initialize()
            except Exception:
                pass
        if self.bus:
            self.bus.publish("ProviderRegistered", {"name": name}, source="OnyxRuntime")

    def register_defaults(self) -> None:
        try:
            from runtime.providers.echo import EchoProvider
        except Exception:
            return
        if "echo" not in self._providers:
            self.register("echo", EchoProvider(self.bus))

    def ask(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        last_err = None
        for i, name in enumerate(list(self._order)):
            prov = self._providers.get(name)
            if prov is None:
                continue
            try:
                ok = prov.send(message, context)
                if self.bus:
                    self.bus.publish(
                        "ProviderUsed",
                        {"name": name, "ok": bool(ok)},
                        source="OnyxRuntime",
                    )
                text = getattr(prov, "_last", None)
                return {"ok": True, "provider": name, "response": text, "sent": bool(ok)}
            except Exception as exc:
                self._failures += 1
                last_err = exc
                nxt = self._order[i + 1] if i + 1 < len(self._order) else None
                if self.bus:
                    self.bus.publish(
                        "ProviderFailover",
                        {"from": name, "to": nxt, "error": str(exc)},
                        source="OnyxRuntime",
                    )
        return {"ok": False, "error": str(last_err or "no providers")}

    def run_loop(
        self,
        goal: str,
        max_steps: int = 8,
        needs_user: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        paused = False
        msg = goal
        cap = max(1, int(max_steps))
        for i in range(cap):
            if self.bus:
                self.bus.publish("WorkflowStep", {"goal": goal, "i": i}, source="OnyxRuntime")
            res = self.ask(msg)
            raw = str(res.get("response") or "")
            rec = {"i": i, "ok": res.get("ok"), "provider": res.get("provider"), "text": raw}
            steps.append(rec)
            if raw.startswith("NEED_USER:"):
                question = raw.split(":", 1)[-1].strip()
                if self.bus:
                    self.bus.publish(
                        "WorkflowNeedsUser",
                        {"question": question},
                        source="OnyxRuntime",
                    )
                if needs_user is None:
                    paused = True
                    break
                msg = needs_user(question)
                continue
            if raw.startswith("DONE:") or i == cap - 1:
                break
            if raw.startswith("NEXT:"):
                msg = raw.split(":", 1)[-1].strip() or goal
            else:
                msg = goal
        if paused:
            if self.bus:
                self.bus.publish("WorkflowNeedsUser", {"goal": goal}, source="OnyxRuntime")
        elif len(steps) >= cap:
            if self.bus:
                self.bus.publish("WorkflowExhausted", {"goal": goal}, source="OnyxRuntime")
        else:
            if self.bus:
                self.bus.publish("WorkflowComplete", {"goal": goal}, source="OnyxRuntime")
        return {
            "ok": bool(steps) and all(s.get("ok") for s in steps) and not paused,
            "goal": goal,
            "steps": steps,
            "paused_for_user": paused,
        }

    def health(self) -> Dict[str, Any]:
        providers = {}
        for name, p in self._providers.items():
            try:
                providers[name] = p.health() if hasattr(p, "health") else {"provider": name}
            except Exception as exc:
                providers[name] = {"provider": name, "error": str(exc)}
        return {"providers": providers, "failures": self._failures, "order": list(self._order)}
