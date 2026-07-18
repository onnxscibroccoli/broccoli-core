class BasePlugin:
    def on_cycle(self, governor): pass
    def on_task(self, task): pass
    def on_decision(self, decision): pass
