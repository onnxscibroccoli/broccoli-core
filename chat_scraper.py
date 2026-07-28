#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BROCCOLI_DIR = Path(os.environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
STATE_PATH = BROCCOLI_DIR / "chat_scraper_state.json"
CONFIG_PATH = BROCCOLI_DIR / "chat_profile.json"
INBOX_PATH = BROCCOLI_DIR / "inbox_response.txt"
OUTBOX_PATH = BROCCOLI_DIR / "outbox_context.txt"
AGENT_MARKERS = ("CMD:", "WRITE_FILE:", "TASK_COMPLETE:")

@dataclass
class ScrapeResult:
    last_message: str = ""
    is_new: bool = False
    message_hash: str = ""
    extracted_agent_block: str = ""
    source: str = "copy_chip"
    error: Optional[str] = None

def load_profile() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

def _normalize(s: str) -> str:
    s = s.replace("\r\n", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", s)

def _hash(s: str) -> str:
    return hashlib.sha256(_normalize(s).encode()).hexdigest()

def _save_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)

def extract_agent_block(text: str) -> str:
    text = _normalize(text)
    for marker in AGENT_MARKERS:
        i = text.find(marker)
        if i >= 0:
            text = text[i:]
            break
    else:
        return ""
    if text.startswith("WRITE_FILE:"):
        m = re.search(r"(?m)^END_WRITE\s*$", text)
        return text[:m.end()].strip() if m else ""
    if text.startswith(("CMD:", "TASK_COMPLETE:")):
        return text.split("\n", 1)[0].strip()
    return text.strip()

def fetch_via_copy_chip() -> tuple[str, str]:
    proc = subprocess.run(
        ["bash", str(BROCCOLI_DIR / "chat_copy_fetch.sh")],
        capture_output=True, text=True, timeout=120, cwd=str(BROCCOLI_DIR),
    )
    if proc.returncode != 0:
        return "", proc.stderr.strip() or "copy_fetch failed"
    return proc.stdout, ""

def set_baseline_after_inject():
    """After we sent outbox to Grok: ignore copies that still match what we sent."""
    out = OUTBOX_PATH.read_text(encoding="utf-8", errors="replace") if OUTBOX_PATH.is_file() else ""
    _save_state({
        "baseline_outbox_hash": _hash(out),
        "last_hash": "",
        "last_seen_ts": int(time.time()),
        "note": "post_inject_wait_for_new_grok_reply",
    })

def scrape_once() -> ScrapeResult:
    state = {}
    if STATE_PATH.is_file():
        try: state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception: pass
    last, err = fetch_via_copy_chip()
    if not last:
        return ScrapeResult(error=err or "empty")
    h = _hash(last)
    baseline_out = state.get("baseline_outbox_hash", "")
    # Still the pasted outbox on clipboard from Copy on user message? Unlikely but skip if equal
    if baseline_out and h == baseline_out:
        return ScrapeResult(last_message=last, is_new=False, message_hash=h, source="copy_chip",
                            error="clipboard still matches sent outbox")
    is_new = h != state.get("last_hash", "__none__")
    block = extract_agent_block(last)
    if is_new and block:
        _save_state({**state, "last_hash": h, "last_message": last[:12000],
                     "last_seen_ts": int(time.time()), "baseline_outbox_hash": ""})
    return ScrapeResult(last, is_new and bool(block), h, block)

def wait_for_new_response(timeout_sec=900, poll_sec=4.0) -> ScrapeResult:
    end = time.time() + timeout_sec
    while time.time() < end:
        r = scrape_once()
        if r.is_new and r.extracted_agent_block:
            return r
        time.sleep(poll_sec)
    return ScrapeResult(error=f"timeout {timeout_sec}s — Grok auto-launched each poll; need new Copy+clipboard")

def write_inbox(res: ScrapeResult) -> bool:
    if not res.extracted_agent_block: return False
    INBOX_PATH.write_text(res.extracted_agent_block + "\n", encoding="utf-8")
    return True

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--wait", type=float)
    ap.add_argument("--write-inbox", action="store_true")
    ap.add_argument("--poll", type=float, default=4.0)
    ap.add_argument("--baseline-after-inject", action="store_true")
    args = ap.parse_args()
    if args.baseline_after_inject:
        set_baseline_after_inject(); print("baseline after inject"); return 0
    r = wait_for_new_response(args.wait or 900, args.poll) if args.wait else scrape_once()
    if args.write_inbox: write_inbox(r)
    print(json.dumps({"is_new": r.is_new, "block": r.extracted_agent_block,
                      "preview": r.last_message[:400], "error": r.error}, indent=2))
    return 0 if not r.error else 1

if __name__ == "__main__": sys.exit(main())
