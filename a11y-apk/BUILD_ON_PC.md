# Build Broccoli A11y APK (one time on PC)

1. Copy folder `~/broccoli/a11y-apk` from phone (or use repo).
2. Install Android Studio OR SDK + Gradle.
3. From `a11y-apk` project root (needs `build.gradle` from Android Studio wizard:
   - Empty Activity OR use existing Kotlin files + manifest already in this folder).

Quick path with Android Studio:
- New project → Empty Views Activity, package `ai.broccoli.a11y`
- Replace `AndroidManifest.xml`, add `BroccoliA11yService.kt`, `A11yCommandReceiver.kt`
- Add `res/xml/a11y_service_config.xml`, `res/values/strings.xml`
- Build → Build APK(s) → debug

4. Copy APK to phone:
   `adb push app/build/outputs/apk/debug/app-debug.apk /sdcard/Download/broccoli-a11y-debug.apk`

5. On phone Termux:
   `bash ~/broccoli/tools/install_a11y_apk.sh`
   `bash ~/broccoli/tools/open_a11y_settings.sh`  # turn service ON
   `bash ~/broccoli/tools/a11y_round_once.sh 'BROCC_TASK reply exactly: LOOP_OK'`
