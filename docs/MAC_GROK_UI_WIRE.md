
# Mac + this chat: wire Grok from UI dump (not chat memory)

## Fixed phrase
Phone dumps Grok UI → Mac syncs `reports/` → parser emits shell → Termux runs `rish`/`brocc`.

## Sync from phone (Termux SSH/rsync)
- ~/broccoli/reports/ui_dump.xml
- ~/broccoli/reports/wire_context.json
- ~/broccoli/reports/ui_snapshot.json
- ~/broccoli/meta/wire_coords.env
- ~/broccoli/reports/agent_loop.log

## Mac: emit runnable commands
python3 pull_wire_from_dump.py --emit-send --msg 'YOUR_MISSION'

Copy output to Termux only (no markdown tables in shell).

## Parallel stack: Mythara (~/project_mythara)
Native agent can also read screen and exec Termux:
- ReadScreenTool.kt / PhoneControlAccessibilityService.kt
- ShizukuService.kt + TermuxExecTool.kt
- minimax/GeminiVisionService.kt (Gemini on device)
Broccoli path is still the one for **Grok app** composer/Send bounds.

## Do not use for wire recon
- Full `tree ~` or Kali rootfs (poppler cMap, 150k files)
- This xAI chat without a fresh dump

## Grok chat export (Mac)
Grep exports for ===GEMINI_RESEARCH_MD===, BROCCOLI_RESEARCH_OK, consume_response.

## Research (RV3→V4.1 RWA)
~/broccoli/reports/research/gemini_rwa_v41.md
