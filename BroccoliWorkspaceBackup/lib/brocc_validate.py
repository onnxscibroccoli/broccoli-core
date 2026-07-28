
"""Reply quality gate for grok control jobs."""
JUNK_PREFIX = (
    "Explore ", "Compare ", "Refine ", "Thoughts",
    "Remove markdown", "Re-queue jobs", "Next: wire",
    "Mac: paste", "Ask phone Grok",
)
JUNK_EXACT = frozenset({"thoughts", "ask", "imagine", "send", "copy"})
def brocc_reply_is_junk(text: str, *, require_loop: bool = False) -> bool:
    t = (text or "").strip()
    if not t or len(t) < 16:
        return True
    if any(x in t for x in ("LOOP_OK", "GROK_SMOKE_OK", "TASK_COMPLETE:", "NEXT_STEP:")):
        return False
    if require_loop and "LOOP_OK" not in t and "TASK_COMPLETE" not in t:
        if len(t) < 120:
            return True
    low = t.lower()
    if low in JUNK_EXACT:
        return True
    if any(t.startswith(p) for p in JUNK_PREFIX):
        return True
    if t.count(chr(10)) < 2 and len(t) < 100:
        return True
    return False
