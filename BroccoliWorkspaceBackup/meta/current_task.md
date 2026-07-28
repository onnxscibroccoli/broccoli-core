# Broccoli continuous agent loop (UI-driven completion)

**ID:** `broccoli_agent_loop_v1`
**Status:** running

CURRENT TASK (authoritative):

Run the Broccoli agent continuously:
1) UI dumps until chat is open; send iter_prompt / loop_inbox (no manual paste when CHAT_OPEN).
2) Capture Grok output → iter_last_output.txt; extract code blocks → sandbox/applied; run quarry_iter.
3) Loop iterations with NO fixed cap until task_complete.decide_complete() says done (UI tokens, quarry, reply).
4) On complete: toast + notification; wait for user_next_task.txt; remind every 60s until a new task is set.
5) Load new task → start_task → repeat forever.

Success criteria:
- agent_loop.py runs in foreground or daemon without requiring manual intervention when chat is open.
- Task queue + current_task.json stay updated each iteration.
- User supplies next work only via ~/broccoli/ui/user_next_task.txt after TASK_COMPLETE.

Do not stop at 8 iterations. Agent decides continue vs complete from UI dumps only.
Reply TASK_COMPLETE when this task is satisfied; otherwise one code block per fix round.
