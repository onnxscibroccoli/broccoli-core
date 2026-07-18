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
