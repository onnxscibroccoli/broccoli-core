import logging

logger = logging.getLogger("accessibility.consumers")

def register_accessibility_consumers(bus, metrics=None):
    """Wires autonomy layer and metrics to accessibility semantic events."""
    
    def on_ui_changed(event):
        payload = event.get("value", {})
        logger.info(f"[UI_CHANGED] UI state aggregated change: {payload}")
        if metrics and hasattr(metrics, 'increment'):
            try: metrics.increment("accessibility.ui_changed", 1)
            except TypeError: metrics.increment("accessibility.ui_changed")

    def on_focus_changed(event):
        payload = event.get("value", {})
        logger.debug(f"[FOCUS_CHANGED] Focus shifted to: {payload.get('focused_id')}")
        if metrics and hasattr(metrics, 'increment'):
            try: metrics.increment("accessibility.focus_changed", 1)
            except TypeError: metrics.increment("accessibility.focus_changed")

    def on_node_added(event):
        payload = event.get("value", {})
        logger.debug(f"[NODE_ADDED] {payload.get('stable_id')}")

    bus.subscribe("UI_CHANGED", on_ui_changed)
    bus.subscribe("FOCUS_CHANGED", on_focus_changed)
    bus.subscribe("NODE_ADDED", on_node_added)
    
    logger.info("Accessibility consumers registered on EventBus.")
