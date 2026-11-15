#!/usr/bin/env python3
"""Draw a simple 144x144 launcher icon (house roof on blue) as PNG using only stdlib."""
import struct, zlib, sys
W = H = 144
def px(x, y):
    # roof triangle
    if 30 <= y <= 72 and abs(x - 72) <= (y - 30) * 1.0 + 6: return (178, 34, 34)
    if 72 < y <= 116 and 40 <= x <= 104:
        if 62 <= x <= 82 and y >= 88: return (90, 60, 30)
        return (245, 240, 230)
    return (25, 90, 160)
raw = b"".join(b"\x00" + b"".join(bytes(px(x, y)) for x in range(W)) for y in range(H))
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
open(sys.argv[1], "wb").write(png)
