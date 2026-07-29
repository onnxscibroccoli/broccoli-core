# KXT + xxd workflow

1. Capture binary on device: `xxd -g 1 -u security.bin > /tmp/sec.xxd`
2. Optional: anchor fields using `research/coordinate_map.json` offsets.
3. Parse in Termux:
   ```python
   from modules.kxt_xxd import parse_xxd, CoordAnchor, verify_security_config
   text = open("/tmp/sec.xxd").read()
   data = parse_xxd(text)
   ```
4. Compare expected platform bytes:
   ```python
   anchors = {"security_flags": CoordAnchor("security_flags", 64, 4)}
   errs = verify_security_config(text, anchors, {"security_flags": b"\x00\x00\x00\x01"})
   ```
5. Round-trip self-test: `dump_via_xxd(data)` should re-parse to same bytes.

Coordinates target **form objects** during dumps; offsets in the map are the authoritative
field locations — not the pixel values themselves.
