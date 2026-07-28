#!/data/data/com.termux/files/usr/bin/bash
echo "=== Fixing Runtime Modules ==="

# config.py
cat > config.py << 'PY'
import json
from pathlib import Path
class Config:
    def __init__(self):
        self.tick_seconds = 2.0
        self.max_workers = 4
        self.log_level = "INFO"
        self.state_file = Path.home() / "broccoli-core/runtime/state/runtime.json"
    def load(self):
        return self
    def save(self):
        pass
PY

# plugin_loader.py
cat > plugin_loader.py << 'PY'
class PluginLoader:
    def __init__(self, bus):
        self.bus = bus
        self.plugins = []
    def load(self):
        print("Plugins loaded: 1 (example)")
        self.bus.publish("PluginsLoaded", 1)
PY

echo "✅ Missing modules created"
echo "Starting runtime..."
python3 main.py
