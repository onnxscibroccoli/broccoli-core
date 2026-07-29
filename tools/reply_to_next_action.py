#!/usr/bin/env python3
"""
Consume phrased Grok reply (from rish UI dump) -> next agent action.
Outputs one line: ACTION|payload  (QUEUE|..., APPLY|..., DONE|..., WAIT|..., FAIL|...)
"""
import json, re, sys
from pathlib import Path

HOME = Path.home()
ITER = HOME / "broccoli/meta/agent_iteration.json"
GROK_LAST = HOME / "broccoli/thread/grok_last.txt"
TASK = HOME / "broccoli/task_box.txt"
Q = HOME / "broccoli/queue/pending.txt"
SANDBOX = HOME / "broccoli/sandbox/from_grok"

def load_iter():
    if ITER.is_file():
        return json.loads(ITER.read_text(encoding="utf-8"))
    return {}

def save_iter(d):
    ITER.parent.mkdir(parents=True, exist_ok=True)
    ITER.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

def last_reply_text():
    if GROK_LAST.is_file():
        lines = [ln.strip() for ln in GROK_LAST.read_text(errors="replace").splitlines() if ln.strip()]
        if lines:
            return lines[-1]
    return ""

def extract_asks(reply: str):
    """Short follow-up prompts Grok might embed."""
    asks = []
    for m in re.finditer(r"(?:^|\n)\s*(?:ASK|Next|Run|Do):\s*(.+)", reply, re.I):
        t = m.group(1).strip()
        if 5 < len(t) < 500:
            asks.append(t)
    if re.search(r"\b(LOOP_OK|GO_OK|HEAL_OK|PHRASE_OK|ITER_OK|APPLY_OK|GO_OK|PASS)\b", reply, re.I):
        asks.append("Reply one word: NEXT_OK")
    return asks[:3]

def has_code_blocks(reply: str) -> bool:
    return "```" in reply or "block_" in reply.lower() or "#!/data/data/com.termux" in reply

def main():
    reply = sys.argv[1] if len(sys.argv) > 1 else last_reply_text()
    prompt = sys.argv[2] if len(sys.argv) > 2 else load_iter().get("last_prompt", "")

    reply = (reply or "").strip()
    if not reply:
        print("WAIT|no_reply_yet")
        return

    d = load_iter()
    d["last_reply"] = reply[:2000]
    d["cycle"] = int(d.get("cycle", 0)) + 1
    d["status"] = "consumed"

    # 1) Code in reply -> apply first
    if has_code_blocks(reply):
        d["status"] = "apply_blocks"
        save_iter(d)
        print("APPLY|extract_grok_code")
        return

    # 2) Explicit completion tokens
    if re.search(r"\b(DONE|COMPLETE|TASK_COMPLETE|FINISHED)\b", reply, re.I):
        d["status"] = "done"
        save_iter(d)
        print("DONE|task_complete")
        return

    # 3) Failure / need research
    if re.search(r"\b(FAIL|ERROR|CANNOT|blocked|moderation)\b", reply, re.I):
        d["status"] = "fail"
        d["next_prompt"] = "Broccoli: wire failed; reply one line fix hint only."
        save_iter(d)
        print("QUEUE|" + d["next_prompt"])
        return


    # Success tokens -> advance task_box, not verbose continue
    if re.search(r"\b(LOOP_OK|GO_OK|HEAL_OK|PHRASE_OK|ITER_OK|APPLY_OK|NEXT_OK|PASS)\b", reply, re.I):
        if TASK.is_file():
            lines = [ln.strip() for ln in TASK.read_text(errors="replace").splitlines() if ln.strip() and not ln.startswith("#")]
            if len(lines) > 1:
                nxt = lines[1][:300]
                d["next_prompt"] = nxt
                d["status"] = "queue_taskbox_next"
                save_iter(d)
                print("QUEUE|" + nxt)
                return
        d["status"] = "ok_token"
        save_iter(d)
        print("WAIT|ok_no_next_task")
        return

    # 4) Follow-up ASKs from reply
    asks = extract_asks(reply)
    if asks:
        nxt = asks[0]
        d["next_prompt"] = nxt
        d["status"] = "queue_next"
        save_iter(d)
        print("QUEUE|" + nxt)
        return

    # 5) Task box drives next if queue empty
    if TASK.is_file():
        for ln in TASK.read_text(errors="replace").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                d["next_prompt"] = ln[:300]
                d["status"] = "queue_taskbox"
                save_iter(d)
                print("QUEUE|" + d["next_prompt"])
                return

    # 6) Continue mission: summarize + ask for next executable step
    nxt = "Broccoli agent: last reply received. Reply with one short ASK line for next wire step only."
    d["next_prompt"] = nxt
    d["status"] = "queue_continue"
    save_iter(d)
    print("QUEUE|" + nxt)

if __name__ == "__main__":
    main()
