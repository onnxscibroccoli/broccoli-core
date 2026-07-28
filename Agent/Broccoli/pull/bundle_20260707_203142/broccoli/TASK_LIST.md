# Broccoli co-dev task list (active)
1. UI dump only — truth from last_ui.xml via rish uiautomator + cat
2. Fix rish dump path — bootstrap dump_ui → ui_dump_rish.sh → ~/broccoli/ui/last_ui.xml
3. No Chrome — launch ai.x.grok via am start -W -n GROK_COMPONENT only
4. show-queue — ./brocc show-queue or show-queue
5. Wire loop — out (send) → poll dump → in (read) → extract 
