# Accubook v0.5 — field UX comparison and export privacy engineering review

**State:** In development, code-level audit + public competitor screenshot assessment; not a physical-device usability claim.  
**Reviewed:** 2026-11-07. **Source:** `experiments/accubook/android/app/src/main/java/com/accubook/crm/`.  
**Product policy:** Field usability, user control and offline reliability outrank feature volume. Do not transplant proprietary layouts.

## Evidence and scope

The two owner-supplied images are **brand references** (Jules Gutter Cleaning leaf and the dog/hardhat app-logo composition), **not screenshots of the running Accubook APK**. This review inspects the current Accubook source hierarchy and documented competitor visuals; a true side-by-side visual A/B of the rendered APK is **not yet possible** without same-device screenshots. Do not present this document as visual regression sign-off.

| Comparator and observed screen | Verified useful affordance | Accubook-specific decision | Unwanted copying |
| --- | --- | --- | --- |
| [Jobber job/visit screen](https://help.getjobber.com/en/articles/jobs-in-the-jobber-app/): separate Visit, Details, Notes; checklists and line items in visit context | **Adopt** in-job contextual switching instead of an endlessly scrolling business record | Focused Job sections: Overview, Photos, Notes, Materials, Costing, Checklists, Schedule where enabled. Keep the current job ID and unsaved-data semantics explicit. | Do not force Jobber's account-centric workflow or its online dependency. |
| [Housecall Pro job creation](https://help.housecallpro.com/en/articles/3181752-how-to-create-a-job) and [job details](https://help.housecallpro.com/en/articles/1153614-the-job-details-page-overview-with-progress-invoicing-and-appointments): prominent primary action and grouped sections | **Adopt** one clear next action per context, information in scannable cards | Keep photo import, reminder, estimate and invoice actions one tap from the correct Job section. | Avoid expanded action bars or selling/upsell UI on a field screen. |
| [AccuLynx field app](https://acculynx.com/new-acculynx-field-app/): calendar and roofing job photo album grid | **Adopt when independently justified:** a dedicated no-friction photo grid for an individual job | Photo section should allow bulk intake, quick preview, optional reordering and evidence labeling. Current bulk intake already owner-tested; gallery/reorder device acceptance remains open. | Avoid imposing a roofing-specific production pipeline on cleaning, landscaping or solo operators. |
| [ServiceTitan Field Mobile job tabs](https://help.servicetitan.com/docs/explore-job-details-and-actions-in-fma): separate job details, forms and invoice; tablet layout differs | **Adopt** task-oriented separation and eventual tablet layout optimization | Turn large enterprise concepts into optional feature switches rather than primary navigation. | No company-wide dispatch, sales funnel, or enterprise configuration tax by default. |
| [Jobber schedule](https://help.getjobber.com/en/articles/schedule-in-the-jobber-app/): day/week/list and color-coded event types | **Conditional** day/week/list views are useful if schedule complexity warrants them | Keep local daybook and user-chosen job colors; hide advanced scheduling in solo mode. | Do not make auto sync mandatory. User-confirmed Calendar editor handoff is baseline. |

## Engineering acceptance — leave existing proven workflows alone

1. **Default visual UX:** compact context sections and simple icon/overflow actions. No persistent oversized Edit/Move controls. Keep long-press affordance discoverable through a small visible overflow menu; TalkBack and keyboard action equivalents must exist.
2. **TalkBack:** Android owns enabling and disabling screen-reading service. Never fake an in-app TalkBack toggle. Accubook can show a shortcut to Android Accessibility settings, and optional extra visual move controls. Semantic labels, focus, contrast and predictable navigation remain baseline even when TalkBack is off.
3. **Local-only model:** no `INTERNET` permission, no runtime AI, no cloud dependency. Feature flags must never erase data. Editing a master job template must not overwrite in-progress job values.
4. **Brand separation:** Jules Gutter Cleaning uses a teal leaf in estimate/invoice branding. Accubook uses the supplied dog/hardhat/wrench mark for the launcher icon and splash. Preserve user-customizable business branding and do not impose Jules branding on unrelated businesses.
5. **Existing working device reports (owner feedback):** photo multi-import, biometric/PIN lock, local dumpster pickup reminders. Calendar automatic sync is not considered reliable; retain the Android user-confirmed event editor as the dependable fallback.

## Reporting interaction contract

**Business > Create an offline business report > Quick PDF summary / Detailed CSV ZIP**. Both paths show the same opt-in selection form, with all sections, payment methods and expense categories **unchecked by default**. The user explicitly selects what is exported and chooses a file destination via Android Storage Access Framework; there is no auto-send or connected QuickBooks account.

**Privacy acceptance invariant:** Excluded payment methods must not appear in direct transaction rows **or derived job-level payment totals and balances**.

- If Payments is disabled but Jobs is included: include recorded job values; **omit** recorded payments and balances entirely in CSV and PDF.
- If Payments is enabled with only Card selected: receipts and computed balances use only Card records. Cash and Cash App totals must not contribute even indirectly.
- If Expenses is disabled, no expenses table or subtotals; if selected, only checked expense categories appear.
- ZIP contains only selected CSV tables plus explanatory scope/limitations. PDF is a human-readable summary, not a general-ledger posting file or audited financial statement.
- Filtering is deterministic, offline, immutable after validation, and tested by `ReportPrivacySmoke` via the Accubook debug APK CI workflow.
- QuickBooks import schema varies by account and region. CSV files are for **manual review/mapping**, not guaranteed one-click import. See [Intuit import scope](https://quickbooks.intuit.com/learn-support/en-us/help-article/import-export-data-files/common-questions-importing-data-quickbooks-online/L4OYJRFdj_US_en_US).

## Validation before production claim

| Check | State |
| --- | --- |
| JVM selected-payment aggregation / exclude Cash and Cash App | Locally verified; exact-head CI still required |
| Data-derived CSV/PDF job subtotal wiring | Code updated; APK compilation and synthetic export validation pending |
| UI screen composition on Android 15, both small and large font | Not verified |
| Real TalkBack navigation and keyboard/switch focus | Not verified |
| Selected PDF versus ZIP contents (fixture accounts, no real private data) | Not verified on device |
| Existing photo import, native unlock and reminders after change | Owner-verified pre-change; regression retest pending |
| Export with explicit no-cash and no-Cash-App selection | Unit helper verified; end-to-end redaction test pending |
| QuickBooks external import acceptance | Not claimed; user-mediated mapping only |

**Next implementation:** finish rendered-screen screenshot audit and synthetic PDF/ZIP contents tests before any product launch announcement.
