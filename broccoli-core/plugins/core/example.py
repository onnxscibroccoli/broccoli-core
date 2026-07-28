from plugins.core.base import Plugin

class ExamplePlugin(Plugin):
    def initialize(self):
        print("✅ Example Plugin loaded")
        return True

    def execute(self, context):
        print(f"🔌 Plugin executed with: {context.get('action')}")
        return {"status": "ok", "result": "plugin output"}

    def health(self):
        return True
