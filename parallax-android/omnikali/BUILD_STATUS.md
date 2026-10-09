# OmniKali Workstation APK Build

Build target: `:omnikali:assembleDebug`

Target SDK: Android 35. CI uses GitHub-hosted Linux, Java 17, Gradle 8.9, and Android SDK platform/build-tools 35.

The debug APK is considered delivered only after GitHub Actions reports a successful build and uploads `omnikali-android-debug-apk`. The OCI workstation is ARM64 Oracle Linux with only 2.3 GB free, so compilation is delegated to GitHub Actions instead of consuming local disk or changing AWS resources.
