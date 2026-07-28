#!/usr/bin/env python3
"""Build grok-ask prompt from project state + this chat loop."""
import sys
from pathlib import Path
ROOT = Path.home() / "broccoli"
THREAD = ROOT / "thread" / "conversation.md"
PROJECT = ROOT / "PROJECT.md"
LATEST = ROOT / "reports" / "latest.txt"

def read(p, n=2500):
    if not p.is_file():
        return ""
    t = p.read_text(errors="replace")
    return t[-n:] if len(t) > n else t

def main():
    job_path = Path(sys.argv[1])
    job = job_path.read_text(errors="replace").strip()
    proj = read(PROJECT, 1200)
    last = read(LATEST, 1800)
    thread = read(THREAD, 4000)
    pending = read(ROOT / "user" / "PENDING.md", 1500) or "(none)"
    task = read(ROOT / "tasks" / "current" / "TASK.md", 2000) or "(no TASK)"
    prompt = "\n".join([
        "You are co-developing Broccoli (Termux + Shizuku UI automation on Android).",
        "Apply lessons from BROCCOLI CONTEXT below; do not repeat fixed issues.",
        "",
        "=== USER RE-ENTRY ===", pending, "", "=== TASK ===", task, "", "=== BROCCOLI CONTEXT ===",
        "--- PROJECT ---",
        proj or "(no PROJECT.md yet)",
        "",
        "--- LAST REPORT ---",
        last or "(no prior report)",
        "",
        "--- CONVERSATION THREAD (recent) ---",
        thread or "(empty — first turn)",
        "",
        "=== RULES ===",
        "TERMINUX: raw python3 << only, no markdown fences.",
        "FORBIDDEN: Thoughts-only or empty reply — always NEXT_STEP + TERMINUX + TEST + REPORT_FOR_MAC.",
        "- Send: tap send button (~1001,1338), never Enter.",
        "- clear_composer: disabled (was hanging).",
        "- Google jobs: Search -> AI Mode, not Gemini app.",
        "- Output for automation:",
        "  NEXT_STEP: (one line)",
        "  TERMINUX: (one paste-only heredoc block, no markdown fences)",
        "  TEST: (one command + expected PASS line)",
        "  REPORT_FOR_MAC: (max 8 lines, pasteable; no XML dumps)",
        "",
        "=== OUTPUT CONTRACT ===",
        "First line of assistant reply MUST be exactly: LOOP_OK",
        "Then NEXT_STEP: one line. Then TERMINUX/TEST/REPORT_FOR_MAC as needed.",
        "",
        "=== THIS JOB ===",
        job,
    ])
    sys.stdout.write(prompt)

if __name__ == "__main__":
    main()
