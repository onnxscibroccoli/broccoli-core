"""Build Grok/Broccoli chat prefix from task queue + last reports."""
from pathlib import Path

def build_prefix(include_smoke=True, max_chars=3500):
    home = Path.home()
    parts = []
    paste = home / "broccoli/reports/task_queue_paste_block.txt"
    if paste.exists():
        parts.append(paste.read_text(errors="replace"))
    if include_smoke:
        sc = home / "broccoli/meta/smoke_cache.json"
        if sc.exists():
            parts.append("\n[smoke_cache]\n" + sc.read_text(errors="replace")[:800])
    wf = home / "broccoli/reports/workflow_front.txt"
    if wf.exists():
        parts.append("\n[workflow_front]\n" + wf.read_text(errors="replace"))
    text = "\n".join(parts)
    return text[:max_chars]

def wrap_user_message(user_text):
    prefix = build_prefix()
    if not prefix.strip():
        return user_text
    return prefix + "\n\n--- USER MESSAGE ---\n" + user_text

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "wrap":
        print(wrap_user_message(sys.stdin.read()))
    else:
        print(build_prefix())
