from __future__ import annotations

from runtime.plugin_loader import PluginLoader


class PluginLoaderTransport:
    """
    Supervised startup transport for the plugin bootstrap phase.

    The loader itself remains simple; this adapter gives it a transport-style
    lifecycle so the registry and governor can report and supervise it.
    """

    def __init__(self, plugin_loader: PluginLoader, name: str = "plugin_loader"):
        self.name = name
        self.plugin_loader = plugin_loader
        self._running = False
        self._loaded = False
        self._last_error = None

    def start(self):
        if self._loaded:
            self._running = True
            return self

        try:
            self.plugin_loader.load()
            self._loaded = True
            self._last_error = None
            self._running = True
        except Exception as exc:
            self._last_error = str(exc)
            self._running = False
            raise
        return self

    def stop(self):
        self._running = False
        return self

    def health(self):
        return {
            "running": self._running,
            "loaded": self._loaded,
            "last_error": self._last_error,
        }
