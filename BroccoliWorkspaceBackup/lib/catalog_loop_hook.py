from __future__ import annotations
import sqlite3, subprocess
from pathlib import Path
HOME, BRO = Path.home(), Path.home() / "broccoli"
DB = HOME / "brocc-inbox" / "chat_catalog.db"
EVERY = int(__import__("os").environ.get("BROCC_CATALOG_EVERY", "5"))

def similar_context(query: str, limit: int = 3) -> str:
    if not DB.is_file() or len(query) < 3:
        return ""
    q = "%" + query[:120].replace("%", "") + "%"
    try:
        with sqlite3.connect(DB) as c:
            rows = c.execute(
                "SELECT c.platform,a.display_name,c.title,c.summary FROM conversations c "
                "JOIN accounts a ON a.id=c.account_id WHERE c.summary LIKE ? OR c.title LIKE ? "
                "ORDER BY c.last_scraped_ts DESC LIMIT ?", (q, q, limit)).fetchall()
        if not rows:
            return ""
        return "BROCC_CONTEXT similar_chats:\n" + "\n".join(
            f"- [{p}/{a}] {t}: {s[:200]}" for p, a, t, s in rows)
    except Exception:
        return ""

def maybe_catalog(round_n: int) -> None:
    if round_n % EVERY:
        return
    sh = BRO / "tools" / "catalog_all_chats.sh"
    if sh.is_file():
        subprocess.Popen(["bash", str(sh)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def enrich_outgoing(text: str) -> str:
    ctx = similar_context(text)
    return (ctx + "\n\n" + text)[:12000] if ctx and "BROCC_CONTEXT" not in text else text

def is_catalog_ok(msg: str) -> bool:
    return "CATALOG_OK" in (msg or "").upper()
