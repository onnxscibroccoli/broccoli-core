# Ruto + Rish virtual-surface bridge

**Status:** live mechanism proven on Samsung Android; production adapter under validation.

Broccoli's secondary/background Android surface is Ruto running through Shizuku/Rish. The working display mechanism is Android's `VirtualDisplayAdapter`, not `overlay_display_devices`.

## Proven live evidence — 2026-10-01

- Ruto package `com.rosan.ruto` was running with its input-method service active.
- Ruto created private 1080x2408 / 420-dpi virtual displays owned by `com.android.shell`.
- Earlier live state had displays 27, 28, and 29, with Termux on 28 and ChatGPT on 29.
- A fresh Ruto create flow produced display 30; a second Ruto display 31 was also observed.
- Ruto's decompiled service exposes `IActivityManager.startApp(package, displayId)`.
- That implementation uses `ActivityOptions.setLaunchDisplayId`, a display-scoped Context, and a PendingIntent.

## Critical launch invariant

Direct shell launch is **not equivalent** to Ruto attachment.

`am start --display <id> ...` was tested against Ruto displays. It could leave an ActivityRecord/task but did not keep Grok's process/window alive. A later direct launch against live display 31 again terminated the Grok process and the Ruto displays disappeared.

By contrast, Ruto's own sequence produced all required evidence for Grok on display 30:

- live `ai.x.grok` PID;
- task on display 30;
- drawn, visible window with `mHasSurface=true`;
- SurfaceFlinger layers for Grok;
- SurfaceFlinger display 30 named `Virtual Screen`.

Therefore Broccoli must never use direct display launch as a recovery fallback.

## Broccoli adapter

`tools/rish_display.py` implements the provider-agnostic `VirtualSurface` contract. It:

1. discovers only Ruto-owned private virtual displays;
2. navigates Ruto by accessibility semantics such as `Screens`, `Screen List`, `Create Screen`, and `Select App`;
3. uses the durable shared-storage UI dump surface under `/sdcard/OmniKali/ui`;
4. verifies display + task + process + drawn window + SurfaceFlinger evidence before reporting ready;
5. fails closed when evidence is incomplete.

The adapter intentionally does not guess display-release semantics. `destroy()` remains unsupported until that Ruto UI action is independently reproduced and verified.
