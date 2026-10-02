# AutoJS Status (2026-10-02)

## Implementation
- Primary runner: `scripts/autojs_run.py`
- Optional consumer: `scripts/grok_validate_reply.py` (gated by `BROCC_USE_AUTOJS=1`)
- Scripts expected on device: `/sdcard/broccoli/autojs/*.js`
- Default package: `org.autojs.autojs6`

## Current Device State
- Running process observed: `org.autojs.autojs.modify`
- Package name mismatch with script default → AutoJS path currently unreliable
- APKs previously quarantined under `quarantine/dupes/`

## Decision Needed
- Align installed package with `org.autojs.autojs6`, **or**
- Update `AUTOJS_PKG` default / make it configurable, **or**
- Retire AutoJS path in favor of pure Rish + UIAutomator (preferred long-term for the rish-bridge work)
