# OCI VNC Display Auto-Repair

The current OCI XFCE/noVNC desktop uses display :1. The watchdog restores 1360x768 when the framebuffer is resized to a narrow portrait resolution, with 1280x720 as a fallback. It disables screen blanking and starts from XFCE autostart. A flock lock prevents duplicate watchdogs.

## Install on the OCI workstation

Run from the repository root as the grasshopper desktop user:

    bash ops/oci/install-vnc-display-watchdog.sh

No root access or additional packages are required beyond standard flock, xrandr, and XFCE/X11 tools already on the host. Runtime log: ~/.omnikali/display-watchdog.log.

## Verification

    DISPLAY=:1 xrandr --current | head -3
    tail -20 ~/.omnikali/display-watchdog.log

Expected framebuffer is 1360 x 768. The top XFCE panel remains 26 px tall and maximized windows retain titlebar decorations. The Android app's direct VNC shortcut uses the existing HTTP noVNC endpoint; configure HTTPS before using it over untrusted networks.
