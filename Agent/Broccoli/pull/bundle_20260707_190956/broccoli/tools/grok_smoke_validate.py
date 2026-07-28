#!/usr/bin/env python3
"""After bootstrap dump file exists, validate smoke from XML."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "broccoli/lib"))
from grok_xml_parse import find_smoke_ok

def main():
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "broccoli/ui/last_ui.xml"
    if not p.exists():
        print("FAIL no xml"); sys.exit(1)
    xml = p.read_text(errors="replace")
    hit = find_smoke_ok(xml)
    if hit:
        print("PASS", hit)
        sys.exit(0)
    print("FAIL", repr(hit))
    sys.exit(1)

if __name__ == "__main__":
    main()
