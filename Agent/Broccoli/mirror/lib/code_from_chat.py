"""Extract and return code blocks from Grok assistant text."""
import re
from pathlib import Path

BLOCK_RE = re.compile(
    r"```(?:bash|sh|shell|python3?|py)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
INLINE_INSTALL = re.compile(r"python3\s*<<\s*['\"]END['\"]\s*\n(.*?)END", re.DOTALL)

def extract_blocks(text):
    if not text:
        return []
    blocks = []
    for m in BLOCK_RE.finditer(text):
        body = m.group(1).strip()
        if len(body) > 20:
            blocks.append(body)
    if not blocks:
        m = INLINE_INSTALL.search(text)
        if m:
            blocks.append(m.group(1).strip())
    return blocks

def extract_from_file(path):
    p = Path(path)
    if not p.exists():
        return []
    return extract_blocks(p.read_text(errors="replace"))

def classify_block(body):
    b = body.lstrip()
    if b.startswith("#!/") or "python3 <<" in body[:80] or "apt install" in body[:200]:
        return "shell"
    if b.startswith("import ") or b.startswith("from ") or "def " in body[:500]:
        return "python"
    return "shell"

def write_applied(blocks, apply_dir):
    apply_dir = Path(apply_dir)
    apply_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, body in enumerate(blocks):
        kind = classify_block(body)
        if kind == "python" and not body.startswith("#!/"):
            ext, runner = ".py", ["python3"]
        else:
            ext, runner = ".sh", ["bash"]
        path = apply_dir / f"round_{i:02d}{ext}"
        if ext == ".sh" and not body.startswith("#!"):
            body = "#!/data/data/com.termux/files/usr/bin/bash\nset -e\n" + body
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        manifest.append({"path": str(path), "kind": kind, "runner": runner[0], "chars": len(body)})
    return manifest
