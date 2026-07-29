#!/data/data/com.termux/files/usr/bin/bash
# No APK: paste + focus + Enter only (no coordinate grid)
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
TASK="${1:-BROCC_TASK reply exactly: LOOP_OK}"
termux-clipboard-set "$TASK" 2>/dev/null || true
printf '%s\n' "$TASK" > "$BRO/inbox/prompt.txt"
python3 <<PY
import sys, json, time
sys.path.insert(0, "$BRO/lib")
from broccoli_a11y_rish import a11y_status
from broccoli_a11y_send import full_round_a11y
st = a11y_status()
if st["installed"] and st["enabled"]:
    print(json.dumps(full_round_a11y("$TASK"), indent=2)[:4000])
else:
    from broccoli_rish_shell import shell
    from broccoli_ui_dump import ui_dump, nodes, last_reply_text, find_grok_search_box
    from broccoli_input import clip_set, wait_for_search_box, task_already_in_composer
    GROK = "ai.x.grok"
    TASK = "$TASK"
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.5)
    clip_set(TASK)
    box, xml, _ = wait_for_search_box(GROK, 4.0)
    if box and not task_already_in_composer(nodes(xml), box, TASK):
        shell(f"input tap {int(box['cx'])} {int(box['cy'])}")
        time.sleep(0.1)
        shell("input keyevent 122")
        shell("input keyevent 279")
    shell(f"input tap {int(box['cx']) if box else 540} {int(box['cy']) if box else 2200}")
    time.sleep(0.15)
    for _ in range(4):
        shell("input keyevent 66")
        time.sleep(0.2)
    before = last_reply_text(nodes(ui_dump()), GROK)
    t0 = time.time()
    last = ""
    while time.time() - t0 < 28:
        shell("input swipe 540 1500 540 800 200")
        time.sleep(0.1)
        ta = last_reply_text(nodes(ui_dump()), GROK)
        if ta and ta != before and len(ta) >= 3:
            open("$BRO/inbox/grok_reply.txt","w").write(ta)
            print(json.dumps({"ok":True,"via":"fallback_enter","loop_ok":"LOOP_OK" in ta,"reply":ta[:300]}, indent=2))
            break
        if len(ta) > len(last): last = ta
    else:
        print(json.dumps({"ok":False,"via":"fallback_enter","need_apk":True,"a11y":st}, indent=2))
PY
