# Multi-agent OnDevice bridge

Repo: `onnxscibroccoli/broccoli-core`  
Branch: `main`  
Device daemon: `bin/broccoli-sync loop`  
Phone root: `$HOME/broccoli-core`

## Who can do what

| Actor | Can push to GitHub? | Reaches the phone? |
|---|---|---|
| Grok in this chat (GitHub connector as `onnxscibroccoli`) | Yes | After device fetch |
| ChatGPT | Only if that ChatGPT session has GitHub write access to this repo | Same daemon |
| User on Termux | `git commit` / `git push` | Immediate |

ChatGPT does **not** inherit Grok's connector. Give ChatGPT this file plus `prompts/chatgpt_bridge.md`.

If ChatGPT cannot push, it must output a patch block. The user pastes that to Grok with: `push this to broccoli-core main`. Grok pushes. The daemon pulls.

## Contract the phone will run

After `git fetch` + fast-forward:

1. `ondevice/hooks/post-sync.sh`
2. Each `ops/ondevice-inbox/*.json` (allowlisted actions only), then move to `ops/ondevice-done/`

Allowed inbox `action` values:

- `health`
- `chmod_bins`
- `brocc` with args from `{status,ping,probe,smoke,help,user-done,log,report}` only
- `python_module` with module matching `[A-Za-z_][A-Za-z0-9_.]*`

Forbidden for every agent:

- credential harvest, virtual-display login, CAPTCHA/rate-limit bypass
- `curl | bash`, `eval`, arbitrary shell inbox actions
- force-push, `git reset --hard` on the phone
- committing tokens (`~/.broccoli/xai_oauth_tokens.json`)
- overwriting untracked OnDevice files without an explicit preserve copy (`tools/rish_display.py` is currently untracked and must be preserved)

## How an agent ships work

1. Read current `main`. Do not assume the phone matches HEAD if status was `dirty_skipped`.
2. Smallest coherent patch. Prefer new files under `runtime/`, `providers/`, `ondevice/`, `ops/`.
3. Never commit consumed inbox JSON that the daemon will delete (that dirties the tree).
4. Optional: add `ops/ondevice-inbox/NNN-<name>.json` with an allowlisted action.
5. Commit to `main` (or hand the patch to an agent who can).
6. Phone loop interval is 45s. Look for `$HOME/.broccoli/sync.log`.

## OnDevice files to preserve (do not clobber)

- `tools/rish_display.py`
- `tools/actions.py`
- `tests/test_actions.py`
- stash `ondevice-tests-*`
- `$HOME/.broccoli/preserve/`

## Workaround routing

Need GitHub write, dirty-tree surgery, or connector work → **Grok**.  
Need design text, tests, or a patch ChatGPT can author but not push → **ChatGPT outputs the patch, Grok or the user commits it**.
