
Broccoli A11y Helper (one-time install)
=======================================
Why: input tap misses Send; Accessibility performs ACTION_CLICK on the real node.

1) Build/install APK with applicationId ai.broccoli.a11y
   (Android Studio: open a11y-apk, Run on device)

2) Settings → Accessibility → Installed apps → Broccoli A11y Helper → ON

3) Termux (Rish):
   bash ~/broccoli/tools/a11y_probe_rish.sh
   bash ~/broccoli/tools/a11y_round_once.sh 'BROCC_TASK reply exactly: LOOP_OK'

Broadcast contract (Rish runs am broadcast):
  action: com.broccoli.a11y.ACTION
  package: ai.broccoli.a11y
  extras: op=click_send|click_text|set_text_focused|click_rid
          target_pkg=ai.x.grok
          text=...

No coordinate files. Strategy logged in ~/broccoli/meta/working_paths.json
