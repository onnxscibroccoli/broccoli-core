#!/usr/bin/env python3
"""CLIP prompt helper — matches core signature: build_prompt(text, *, max_len=77)."""
from typing import Optional

def build_prompt(text: str, *, max_len: int = 77) -> str:
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 3].rstrip() + "..."

def main():
    import sys
    raw = sys.stdin.read() if not sys.argv[1:] else " ".join(sys.argv[1:])
    sys.stdout.write(build_prompt(raw))

if __name__ == "__main__":
    main()
