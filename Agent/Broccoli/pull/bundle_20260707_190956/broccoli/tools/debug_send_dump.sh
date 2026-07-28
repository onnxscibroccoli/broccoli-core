#!/data/data/com.termux/files/usr/bin/bash
bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null
echo "=== composer / send candidates ==="
grep -E 'chat_text_input|EditText|send|Send|ImageButton|submit' "$HOME/broccoli/ui/last_ui.xml" | head -25
python3 "$HOME/broccoli/tools/find_send_tap.py" 2>&1 | tail -3
