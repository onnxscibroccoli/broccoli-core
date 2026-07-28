Mac:
  adb pull /sdcard/Broccoli/pull .
  OR rish: cat /sdcard/Broccoli/pull/manifest_latest.json
Phone:
  brocc pull-rish
  brocc ask 'LOOP_OK\nNEXT_STEP: Mac pull manifest_latest.json'
