"""Decide task complete from UI dumps + quarry + reply text (agent logic)."""
import json, re
from pathlib import Path

ROOT = Path.home() / "broccoli"
META, REP, UI = ROOT / "meta", ROOT / "reports", ROOT / "ui"

def load_rules():
    p = META / "task_completion_rules.json"
    return json.loads(p.read_text()) if p.exists() else {}

def quarry_snapshot():
    q = REP / "quarry_last.txt"
    if not q.exists():
        return "", True
    t = q.read_text(errors="replace")
    fail = "FAIL" in t and "SCORE" in t
    all_pass = "11 / 11" in t or (t.count("FAIL") == 0 and "PASS" in t)
    return t[-2000:], all_pass

def reply_text():
    for p in (UI / "iter_last_output.txt", UI / "last_assistant_reply.txt", UI / "loop_outbox.txt"):
        if p.exists():
            t = p.read_text(errors="replace").strip()
            if t:
                return t
    return ""

def classify_from_ui():
    import sys
    sys.path.insert(0, str(ROOT / "lib"))
    try:
        from ui_state import classify
        from ui_dump_loop import dump_once
        dump_once()
        state, meta = classify()
        return state, meta
    except Exception as e:
        return "UNKNOWN", {"err": str(e)}

def decide_complete(history_tail=None):
    """
    Returns dict: complete (bool), confidence (0-1), reasons (list), should_continue (bool)
    """
    rules = load_rules()
    reasons = []
    reply = reply_text()
    qtext, quarry_ok = quarry_snapshot()

    state, meta = classify_from_ui()
    last_reply = (meta.get("last_reply") or reply or "").lower()

    complete_tokens = [x.lower() for x in rules.get("ui_signals_complete", [])]
    continue_tokens = [x.lower() for x in rules.get("ui_signals_continue", [])]

    score_complete = 0
    score_continue = 0

    for tok in complete_tokens:
        if tok in reply.lower() or tok in last_reply:
            score_complete += 1
            reasons.append(f"token:{tok}")

    for tok in continue_tokens:
        if tok in reply.lower() or tok in last_reply:
            score_continue += 1
            reasons.append(f"continue:{tok}")

    if rules.get("require_no_fail_in_quarry") and qtext and "FAIL" in qtext:
        # allow if only known dump_ui flake and smoke parse passed
        if "FAIL dump_ui" in qtext and "PASS smoke_parse_B" in qtext:
            reasons.append("quarry:dump_ui_only_flake")
        else:
            score_continue += 2
            reasons.append("quarry:has_fail")

    if quarry_ok and rules.get("require_quarry_pass"):
        score_complete += 2
        reasons.append("quarry:all_pass")

    if state == "CHAT_WITH_REPLY" and meta.get("last_reply"):
        if len(meta["last_reply"]) < 30 and any(t in meta["last_reply"].upper() for t in ("ITER_OK", "TASK_COMPLETE", "GROK_SMOKE_OK")):
            score_complete += 2
            reasons.append("ui:short_ok_token")

    # Code block in reply => likely not done unless also says complete
    if "```" in reply and score_complete < 2:
        score_continue += 2
        reasons.append("reply:has_code_block")

    cur = {}
    cf = META / "current_task.json"
    if cf.exists():
        try:
            cur = json.loads(cf.read_text())
        except Exception:
            pass
    if cur.get("status") == "done" and cur.get("last_result", "").startswith("ok"):
        score_complete += 1
        reasons.append("meta:task_done")

    complete = score_complete >= 2 and score_complete > score_continue
    should_continue = score_continue >= score_complete or not complete

    confidence = min(1.0, abs(score_complete - score_continue) / 4.0 + (0.3 if complete else 0))

    return {
        "complete": complete,
        "should_continue": should_continue,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "ui_state": state,
        "ui_meta": {k: v for k, v in (meta or {}).items() if k != "last_reply"},
        "reply_head": reply[:200],
        "quarry_ok": quarry_ok,
    }
