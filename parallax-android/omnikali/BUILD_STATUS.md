# OmniKali Workstation APK Build

Build target: :omnikali:assembleDebug

Target SDK: Android 35. CI uses GitHub-hosted Linux, Java 17, Gradle 8.9, and Android SDK platform/build-tools 35.

## Workstation integration

- The native Workspaces and Browser sections include a direct shortcut to the existing OCI noVNC desktop at 129.213.28.18.
- The URL requests auto-connect, scale-to-fit, and reconnect.
- The Android network security config permits cleartext traffic only to the existing OCI host. All other app traffic remains HTTPS-only.
- OCI XFCE display watchdog and autostart installer are tracked under ops/oci. Live verification deliberately changed the framebuffer to 411x788; the watchdog restored it to 1360x768 within five seconds. The top panel remains visible and XFCE borderless maximize is disabled.
- The current OCI noVNC endpoint is HTTP, not TLS. Avoid using it on untrusted networks until HTTPS is configured.

## Scope and validation

The APK is considered delivered only after GitHub Actions reports a successful build and uploads omnikali-android-debug-apk. The OCI workstation is ARM64 Oracle Linux with only about 2.3 GB free on root, so compilation is delegated to GitHub Actions instead of consuming local disk or changing AWS resources.

The desktop shortcut and responsive WebView are implemented. Authenticated remote terminal sessions, production Helix API/session-ticket integration, live cloud Android controls, and server-side Playwright job execution remain NOT_PROVEN and are not represented as working features.
