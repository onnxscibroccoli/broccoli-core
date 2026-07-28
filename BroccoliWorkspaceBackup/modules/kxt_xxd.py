"""KXT — parse xxd(1) hex dumps into bytes; map coordinate anchors to offsets."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

XXD_LINE = re.compile(
    r"^([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*)$"
)

@dataclass
class XxdRegion:
    offset: int
    data: bytes
    ascii_tail: str

def parse_xxd(text: str) -> bytes:
    """Reconstruct binary from xxd -g1 style lines (also tolerates -g2 groups)."""
    chunks: List[Tuple[int, bytes]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("-"):
            continue
        m = XXD_LINE.match(line)
        if not m:
            continue
        off = int(m.group(1), 16)
        hexpart = re.sub(r"\s+", "", m.group(2))
        if len(hexpart) % 2:
            continue
        chunks.append((off, bytes.fromhex(hexpart)))
    if not chunks:
        return b""
    chunks.sort(key=lambda x: x[0])
    out = bytearray()
    cursor = 0
    for off, blob in chunks:
        if off > cursor:
            out.extend(b"\x00" * (off - cursor))
        elif off < cursor:
            # overlapping tail: skip duplicate prefix
            skip = cursor - off
            blob = blob[skip:]
            off = cursor
        out.extend(blob)
        cursor = off + len(blob)
    return bytes(out)

def dump_via_xxd(binary: bytes, cols: int = 16) -> str:
    """Produce xxd-compatible text for round-trip tests."""
    lines = []
    for i in range(0, len(binary), cols):
        chunk = binary[i : i + cols]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:08x}: {hexs:<{cols*3}}  {asc}")
    return "\n".join(lines)

@dataclass
class CoordAnchor:
    """UI/form object id -> byte offset in security blob (from platform map)."""
    name: str
    offset: int
    length: int

def read_field(data: bytes, anchor: CoordAnchor) -> bytes:
    end = anchor.offset + anchor.length
    if anchor.offset < 0 or end > len(data):
        raise ValueError(f"anchor {anchor.name} out of range")
    return data[anchor.offset:end]

def verify_security_config(
    xxd_text: str,
    anchors: Dict[str, CoordAnchor],
    expected: Dict[str, bytes],
) -> List[str]:
    data = parse_xxd(xxd_text)
    errors = []
    for key, exp in expected.items():
        if key not in anchors:
            errors.append(f"missing anchor: {key}")
            continue
        got = read_field(data, anchors[key])
        if got != exp:
            errors.append(f"{key}: got {got.hex()} expected {exp.hex()}")
    return errors
