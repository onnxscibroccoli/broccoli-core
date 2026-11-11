# Accubook Draft-Branch Errors and Gaps (Nov 5-7 Stack)

**Source:** Testing notes from draft branches `feat/accubook-offline-android-debug-20261105`, `feat/accubook-integrated-crm-20261106`, and related PRs (#81, #82). Not exhaustive; acceptance gates in #83 remain open.

## Known Errors / Incomplete Behaviors

1. **Incomplete integrated workflows** — Customer card not fully tappable with complete history; contact chooser cancel path may create partial records in some edge cases; scheduler lacks full recurrence/capacity/conflict handling.

2. **Data atomicity** — Multi-file writes are not transactional. Job index totals are denormalized caches. Crash between writes can leave inconsistent state. Journal/replay not yet implemented (see PRODUCT_REQUIREMENTS).

3. **Encryption** — Active workspace remains plaintext CSV. Only optional export encryption (ACBK2) exists. No device-keystore envelope for customers/notes/payments at rest (#86).

4. **Backup/Restore** — Restore path incomplete; ZIP traversal/bomb defenses, integrity signatures, and fault-injection tests pending. Uninstall deletes app-private data without warning in all flows.

5. **Photos & Attachments** — Full-res storage, thumbnail bounding, before/during/after classification, and annotation incomplete. Metadata stripping not verified.

6. **Payments & Accounting** — Offline cash/check ledger allocations, refunds, A/R aging partial. Online adapters must remain strictly opt-in and never labeled offline.

7. **Search & Reports** — Core search exists in drafts but exportable datasets with privacy safeguards and trend reporting incomplete.

8. **Accessibility** — TalkBack, Switch Access, 200% font, reduced motion, keyboard focus not fully audited on real devices. Some controls may be unlabeled.

9. **Build & Device** — Debug APK builds succeed in CI (e.g., run 42157304551) but device installation, crash recovery, and large-contact (>250) performance unproven. No production signing.

10. **Cross-platform** — Android experimental only. Desktop/iOS parity and Tauri path not started.

## Regression Risks from Draft Testing

- Contact import dedupe false positives/negatives.
- Photo attach path memory spikes on low-RAM devices.
- Schedule reschedule not propagating to all dependent records.
- Line-item edit/remove not always updating totals atomically.

**Action:** These must be closed before any release gate pass. See #83 and #86.
