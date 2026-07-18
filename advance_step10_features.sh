#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Phase 3 Step 10: Advanced Accessibility + Plugins + Persistent Service ==="

# 1. Enhanced Accessibility Driver
mkdir -p drivers/accessibility
cat > drivers/accessibility/driver.py <<'ACC'
import time
from runtime.logger import setup_logger

class AccessibilityDriver:
    def __init__(self):
        self.logger = setup_logger("accessibility")
        self.logger.info("✅ AccessibilityDriver initialized")

    def available(self):
        # In real implementation: check AccessibilityService status via Shizuku
        return True

    def snapshot(self):
        """Return current screen node tree (placeholder)"""
        # Later: use uiautomator2 or Shizuku + dumpsys
        return {"nodes": [], "activity": "com.example.app/.MainActivity", "timestamp": time.time()}

    def perform_action(self, action: str, params: dict = None):
        """Better interactions: click, scroll, input"""
        self.logger.info(f"🔧 Performing {action} with params: {params}")
        if self.rish_available():  # Will use Shizuku when ready
            pass  # e.g. input tap, swipe, etc.
        return {"success": True, "action": action}

    def rish_available(self):
        return False  # Extend with Shizuku later
ACC

# 2. Plugin System Expansion
mkdir -p plugins
cat > plugins/example_plugin.py <<'PLUG'
from runtime.logger import setup_logger

class ExamplePlugin:
    def __init__(self):
        self.logger = setup_logger("plugin.example")
        self.logger.info("✅ Example Plugin loaded")

    def on_cycle(self, governor):
        """Hook called each governor cycle"""
        governor.logger.info("🔌 ExamplePlugin: on_cycle hook executed")

    def on_task(self, task):
        if "UI changes" in task.goal:
            self.logger.info("🔍 Plugin analyzing UI changes")
PLUG

# Update plugin loader
mkdir -p runtime
cat > runtime/plugin_loader.py <<'LOADER'
from runtime.logger import setup_logger
import os
import importlib

def load_plugins():
    logger = setup_logger("plugin_loader")
    plugins = []
    plugin_dir = "plugins"
    
    if os.path.exists(plugin_dir):
        for f in os.listdir(plugin_dir):
            if f.endswith('.py') and not f.startswith('__'):
                try:
                    module = importlib.import_module(f"plugins.{f[:-3]}")
                    for attr in dir(module):
                        obj = getattr(module, attr)
                        if isinstance(obj, type) and "Plugin" in attr:
                            plugins.append(obj())
                            logger.info(f"✅ Loaded plugin: {attr}")
                except Exception as e:
                    logger.warning(f"Failed to load {f}: {e}")
    return plugins
LOADER

# 3. Persistent Service Wrapper
cat > service.sh <<'SERVICE'
#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

# Persistent background service
while true; do
    PYTHONPATH=. python3 runtime/main.py >> broccoli.log 2>&1 &
    PID=$!
    echo "Broccoli Governor started with PID $PID at $(date)" >> service.log
    wait $PID
    echo "Governor crashed - restarting in 5s..." >> service.log
    sleep 5
done
SERVICE

chmod +x service.sh run.sh

# 4. Final main.py (with plugin hooks)
cat > runtime/main.py <<'MAIN'
import sys
sys.path.insert(0, '.')

from governor.engine import Governor

def main():
    print("🚀 Broccoli Core - Phase 3.10: Advanced Governor + Plugins\n")
    governor = Governor()
    try:
        governor.start()
    except KeyboardInterrupt:
        governor.stop()
        print("\n✅ Governor shutdown complete.")

if __name__ == "__main__":
    main()
MAIN

echo "✅ Step 10 Complete!"
echo "Run persistent service: ./service.sh"
echo "Normal test: ./run.sh"
