# Accubook Draft-Branch Testing Errors & Gaps

**Reviewed:** Nov 5–7 2026 Accubook draft stack (`feat/accubook-offline-android-debug-20261105`, `feat/accubook-integrated-crm-20261106`, `feat/accubook-security-accounting-ux-20261106`, and related).
**Source:** PRODUCT_REQUIREMENTS.md functional acceptance matrix, issues #83 and #86, branch inspection.
**Status:** These are open gaps. No claim of full device acceptance testing performed in this change.

## Critical Gaps (Block Release)

1. **Backup / Restore not accepted**
   - Staged ZIP restore and structural validation exist.
   - Real-device power-loss, corruption, large-photo, ZIP-bomb, and migration tests pending.
   - Restore must never silently overwrite the only surviving copy.

2. **Active workspace encryption incomplete**
   - Optional export encryption present; canonical CSV workspace remains plaintext.
   - Device-keystore-enveloped keys, authenticated storage for notes/amounts/payments, crash-safe migration, and portable recovery not implemented (issue #86).

3. **Accessibility unverified**
   - TalkBack, Switch Access, 200% font, reduced motion, keyboard focus, contrast, and landscape not device-validated.
   - No gesture-only actions allowed; labels and focus order unconfirmed.

4. **Payments & Financial Correctness missing**
   - Offline cash/check ledger, allocations, partial payments, refunds, A/R aging not implemented.
   - Monetary rounding, tax, invoice state transitions, and payment evidence requirements incomplete.

5. **Scheduler incomplete**
   - Day/week/month date agenda exists; time windows, timezone, recurrence, crew dispatch, capacity/conflicts, and accessible reschedule missing.

6. **Photo evidence partial**
   - Private attachment and preview present; camera capture, annotation, before/during/after classification, and metadata controls missing.

7. **Customer / Property completeness**
   - Basic customer detail and job list exist; archive/merge, multi-contact, full property history, and coherent full history view incomplete.

8. **Installation & Upgrade**
   - Android 8–15 device install, upgrade, and data-preservation on uninstall/upgrade not verified.

9. **Search & Reporting**
   - Global search partial; A/R, pipeline, profitability, and exportable reports with privacy safeguards not implemented.

10. **Cross-platform & Release**
    - Desktop/iOS parity, signing provenance, independent review, and owner acceptance not done.

## Additional Observations from Drafts

- Draft PRs #81/#82 provide partial connected flows (contact picker, search, agenda, notes, materials, photos) but do not satisfy the P0 integrated workflow checkboxes.
- No INTERNET permission in core path is correctly enforced; optional adapters must remain strictly opt-in.
- Fault-injection and journal/replay for multi-file atomicity still require expanded coverage.

## Recommendations

- Prioritize data-safety (encryption + proven backup/restore) before expanding UI.
- Add automated accessibility checks and device matrix in CI where feasible.
- Keep all new voice-mode work on a feature flag and offline-only until core CRM acceptance gates pass.
