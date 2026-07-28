# dev-env-v2 protocol

## Clipboard (mandatory)
broccoli_clipboard.set() -> termux-clipboard-set -> termux-clipboard-get verify -> toast
Fallback: rish -c 'cmd clipboard' or service call if API missing
Never paste without verify match

## CLI
brocc -> exec python3 ~/broccoli_brocc.py "$@"

## Mac co-dev
adb pull /sdcard/Broccoli/pull/CLIPBOARD_LAST.txt && pbcopy
Push jobs: adb push line -> /sdcard/Broccoli/mac/inbox.jsonl

## Install
type=patch in mac/inbox -> broccoli_installer.py (no chat heredoc)

## Visibility
daemon starts: broccoli_pulse.py loop 7

## Branch marker
active_branch: dev-env-v2
