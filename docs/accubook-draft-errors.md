# Accubook Draft-Branch Testing Errors & Blockers

**Branches reviewed:** Nov 5–7 stack
- `feat/accubook-offline-android-debug-20261105`
- `feat/accubook-integrated-crm-20261106`
- `feat/accubook-security-accounting-ux-20261106`
- `feat/accubook-workflows-20261106`
- `feat/accubook-csv-contact-migration-20261107`
- `feat/accubook-custom-workflows-20261107`
- `feat/accubook-inventory-layers-20261107`
- `feat/accubook-inventory-ledger-20261107`
- `feat/accubook-local-annotations-jiggle-20261107`
- `feat/accubook-modular-reporting-20261107`
- `feat/accubook-onboarding-foundation-20261107`
- `feat/accubook-v05-frictionless-reporting-20261107`
- `feat/accubook-v05-report-privacy-20261107`
- `fix/accubook-emulator-smoke-section-tabs-20261107`

## Documented Errors / Gaps (from READMEs, issues, and code inspection)

1. **Not production-ready** – Explicitly labeled experimental. No final debug APK acceptance. Draft PR #81 is 29 KB baseline, not usable-complete. PR #82 adds partial features only.

2. **Multi-file atomicity missing** – Writes use AtomicFile per file but multi-record operations are not journaled. Job index total is denormalized cache. Crash/power-loss can leave inconsistent state. Required: journal/replay.

3. **Backup restore incomplete** – Export exists; full restore with integrity, versioning, rollback, and fault-injection not proven. App-private files deleted on uninstall; must export first.

4. **No runtime AI / cloud** – By design. No INTERNET permission. Good for offline, but limits optional adapters.

5. **Encryption limited** – ACBK2 encrypts optional export only. Active CSV workspace remains plaintext. Active-data encryption at rest (keystore-enveloped) is a P0 blocker (issue #86).

6. **Missing core CRM flows**
   - Full customer history (all jobs/quotes/invoices/photos/payments) not coherent.
   - Contact picker import with review/dedupe incomplete.
   - Scheduler lacks recurrence, crew, conflicts, accessible drag alternative.
   - Prospect → estimate → job → invoice → payment ledger not end-to-end.
   - Photos, annotations, material requests, change orders partial.
   - Payments ledger (allocations, refunds, A/R) not fully implemented.

7. **Accessibility gaps** – TalkBack, Switch Access, 200% font, contrast, focus order not fully validated on device.

8. **Financial correctness** – Monetary rounding, tax, deposits, immutable invoice numbering not proven. Paid status requires payment evidence.

9. **Schema / migration** – CSV codec exists and unit-tested, but full migration/recovery under corruption not stress-tested.

10. **CI / device evidence** – Successful APK builds exist, but device smoke (create customer → schedule → add item → export) and large-contact tests still required.

11. **Supplier / external adapters** – QXO, Lansing, SRS, Google Calendar, QuickBooks blocked on credentials and contracts (issue #86).

12. **Voice / STT** – Not present in draft branches. This document accompanies the voice-mode design.

## Recommendations

- Prioritize data-safety journal and encryption before adding voice or more features.
- Keep all new work on feature branches; do not merge to main until acceptance gates pass.
- Use synthetic data only until owner approval.

Updated as part of voice-mode v1 work. See also issues #83 and #86.
