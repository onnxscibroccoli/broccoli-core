from runtime.logger import setup_logger
from plugins.core.base import BasePlugin

class ExamplePlugin(BasePlugin):
    def __init__(self):
        self.logger = setup_logger("plugin.example")
        self.logger.info("✅ Example Plugin loaded")

    def on_cycle(self, governor):
        governor.logger.info("🔌 ExamplePlugin: on_cycle hook executed")

    def on_task(self, task):
        if "UI" in task.goal or "screen" in task.goal:
            self.logger.info("🔍 Plugin analyzing screen task")

    def on_decision(self, decision):
        self.logger.info(f"🧠 Plugin reacting to decision: {decision.get('action')}")
    def on_cycle(self, governor):
        governor.logger.info("🔌 ExamplePlugin: on_cycle")
        if hasattr(governor, 'overlay') and governor.overlay.is_idle():
            governor.overlay.show_prompt("Plugin suggests: Run accessibility test?")
    def on_cycle(self, governor):
        governor.logger.info("🔌 ExamplePlugin: on_cycle")
        if hasattr(governor, 'overlay') and governor.overlay.is_idle():
            governor.overlay.show_prompt("Plugin suggests: Run accessibility test?")
