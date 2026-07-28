
MAX_COMPOSE_CHARS = 2800
def cap_compose(body: str) -> str:
    b = (body or "").strip()
    if len(b) <= MAX_COMPOSE_CHARS:
        return b
    head = "LOOP_OK\nNEXT_STEP: read tasks/current/TASK.md\n"
    tail = "\n...(context truncated; full thread on disk)..."
    keep = MAX_COMPOSE_CHARS - len(head) - len(tail) - 20
    return head + b[:max(400, keep)] + tail
