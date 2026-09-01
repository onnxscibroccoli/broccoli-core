from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Dict, List, Optional

logger = logging.getLogger("plugin_loader")


class PluginLoader:
    """Discovers and loads runtime plugins from a package path.

    Exposed as a managed transport so the Governor can restart it and the
    transport registry can report its health.
    """

    def __init__(self, package: str = "runtime.plugins") -> None:
        self.package = package
        self._plugins: List[Any] = []
        self._loaded = False
        self._running = False
        self._last_error: Optional[str] = None

    def load(self) -> List[Any]:
        if self._loaded:
            return self._plugins
        try:
            package = importlib.import_module(self.package)
        except Exception as exc:
            self._last_error = f"package import failed: {exc}"
            logger.warning(self._last_error)
            self._loaded = True
            return self._plugins

        for module_info in pkgutil.iter_modules(package.__path__):
            name = f"{self.package}.{module_info.name}"
            try:
                module = importlib.import_module(name)
            except Exception as exc:
                self._last_error = f"{name}: {exc}"
                logger.warning("Plugin load failed for %s: %s", name, exc)
                continue
            plugin = getattr(module, "PLUGIN", None) or getattr(module, "plugin", None)
            if plugin is not None:
                self._plugins.append(plugin)
                logger.info("Loaded plugin: %s", name)
        self._loaded = True
        return self._plugins

    def start(self) -> "PluginLoader":
        if self._running:
            return self
        self.load()
        self._running = True
        return self

    def stop(self) -> "PluginLoader":
        self._running = False
        return self

    def health(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "loaded": self._loaded,
            "plugin_count": len(self._plugins),
            "last_error": self._last_error,
        }
