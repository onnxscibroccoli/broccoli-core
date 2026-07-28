from pathlib import Path

files = {
    "drivers/accessibility/public_backend.py": [
        ("from backend import AccessibilityBackend",
         "from .backend import AccessibilityBackend")
    ],

    "drivers/accessibility/hidden_backend.py": [
        ("from backend import AccessibilityBackend",
         "from .backend import AccessibilityBackend"),
        ("from backend import AccessibilityBackend",
         "from typing import Dict\nfrom .backend import AccessibilityBackend")
    ],

    "drivers/accessibility/manager.py": [
        ("from backend import AccessibilityBackend",
         "from .backend import AccessibilityBackend"),
        ("from public_backend import PublicBackend",
         "from .public_backend import PublicBackend"),
        ("from hidden_backend import HiddenBackend",
         "from .hidden_backend import HiddenBackend"),
        ("from event_bus import EventBus",
         "from event_bus import EventBus")
    ],

    "drivers/accessibility/driver.py": [
        ("from manager import AccessibilityManager",
         "from .manager import AccessibilityManager")
    ]
}

for filename, replacements in files.items():
    path = Path(filename)
    if not path.exists():
        continue

    text = path.read_text()

    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1)

    path.write_text(text)
    print(f"✓ {filename}")

print("\nDone.")
