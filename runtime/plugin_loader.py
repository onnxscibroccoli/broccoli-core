class PluginLoader:
    def __init__(self, bus):
        self.bus = bus
        self.plugins = []
    def load(self):
        print("Plugins loaded: 1 (example)")
        self.bus.publish("PluginsLoaded", 1)
