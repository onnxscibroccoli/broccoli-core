# Accubook — offline-first field-service CRM (engineering preview)

## November 7, 2026 — modular field workflow and private reporting increment

**Implementation:** `feat/accubook-modular-reporting-20261107`. **Acceptance:** not
production-verified; follow the CI and on-device checks below. See
[UX_COMPETITIVE_REVIEW.md](UX_COMPETITIVE_REVIEW.md) for the source-grounded
Jobber / Housecall Pro / JobNimbus comparison and decision record.

- **Six focused sections on every job:** Overview, Notes, Materials, Billing,
  Photos, and optional Time & route. The current job is preserved during tab
  switches and field edits. Optional time and GPS modules are hidden by default.
- **Settings > Features:** local presentation switches for crews, advanced
  scheduling, pricebook, material requests, properties (preview), recurrence
  (preview), worker time, GPS tracking, and extra reorder controls. A disabled
  module's records are never erased. Switching off a feature does not assert
  it is implemented; multiple properties and recurring jobs remain previews.
  Settings are currently Android SharedPreferences; unlike CSV workspace
  records, these UI preferences are **not yet included in backup ZIPs**.
- **Reordering:** master and per-job fields use atomic row-position updates
  with stable field IDs and preserved inactive records; long-press or compact
  `⋯` menu offers Edit, Move up/down and confirmed Delete. Per-job photos
  have a small `⋯` menu; their order is persisted atomically to
  `photos/order.csv`, which is now allow-listed, checked and carried through
  workspace backup/restore. Photo order is independent per job.
- **Quick local PDF or selective ZIP:** Business > Create report lets the
  user choose PDF summary or CSV ZIP, then check the exact tables, payment
  methods, and expense categories. **Nothing is selected by default.**
  Deselecting Cash App, cash or any other ledger excludes its entries.
  Job-total reporting deliberately does not include indirect aggregate
  payment fields that could reveal an excluded ledger. ZIP includes
  `EXPORT_SCOPE.txt` plus manual import guidance.
- **Privacy:** nothing is uploaded or connected to QuickBooks; PDF is generated
  with Android's local `PdfDocument`, ZIP uses standard CSV files. Financial
  records are manual and are **not** a balanced double-entry general ledger,
  payroll system, bank reconciliation, vendor-bill subsystem, audited revenue
  measure, or automatically compatible QuickBooks import format.
- **Accessibility:** visual controls remain compact; a discoverable
  accessibility-labeled `⋯` button is provided alongside long-press,
  with optional extra arrow buttons. Accubook cannot and should not toggle
  Android TalkBack; the user can open Android Accessibility settings from
  Features. Physical TalkBack and keyboard acceptance is still pending.

**Immediate acceptance commands (from `experiments/accubook/android`):**

```bash
gradle :app:assembleDebug --no-daemon
# Regression checks are defined in .github/workflows/accubook-debug-apk.yml
# Device smoke is defined in .github/workflows/accubook-emulator-smoke.yml
```

**Still open:** modern launcher app icon and logo asset integration; physical
device tests; PDF pagination visual QA; expense/ledger export differential
tests; richer accounting models and production signing. Passing CI must not
be labeled a successful customer accounting deployment.

---

> **Security and operations increment:** Read
> [SECURITY_ACCOUNTING_INTEGRATION.md](SECURITY_ACCOUNTING_INTEGRATION.md)
> for verified versus unverified features, supported calendar sharing, supplier
> price-sheet import, app lock, encrypted backup, and the production release
> blockers. This branch is an **engineering preview**, not production software.
>
> The new-workspace default brand is **Jules Gutter Cleaning**,
> 15 Ward Street, Hingham, MA 02043 · 267-667-2321 ·
> julesguttercleaning@gmail.com. Existing brand records are **not overwritten**;
> Business has an explicit profile-apply action.
>
> Live QXO/Lansing/SRS supplier account APIs are **NOT connected**; the app
> accepts owner-imported supplier price CSVs. Calendar account sync is explicitly
> opt-in through Android's Calendar Provider, not a background Google API client.
> Native fingerprint/PIN access lock does not encrypt the active CSV workspace.
> Portable AES-GCM password-encrypted backups are an **additional** safeguard.


## November 7, 2026 — owner-led usability iteration (development)

### Verified user feedback

The owner reported that **local dumpster-reminder notifications, multi-photo import,
and native biometric/device PIN unlock work** on their Android device. Google
Calendar auto-sync did **not** work reliably. Other new changes are code/CI verified
only until physically tested.

### Updated workspaces and workflows

- **Contacts and Customers are separate.** Open **Contacts** > **Import ALL phone
  contacts**. Android asks for contact permission once; Accubook imports the
  permitted phone address book (including contacts without telephone numbers)
  into an independent private `master_data/contacts.csv`. One explicit action
  copies the full set with de-duplication in a single atomic local CSV write.
  Search, browse, add, edit and delete contacts without creating customers.
  From an individual contact choose **Make this contact a customer** to opt
  in to the customer/job relationship. The old user-selected multi-import also
  populates Contacts only; it never silently creates customers.
- **Editable master job template:** Business > **Customize master job fields**.
  Edit, rename, add or remove fields. Supported inputs: checkboxes, free text,
  dates and numeric values, each optionally required. Initial examples include
  site estimate visit, materials delivered, dumpster delivered/picked up and
  site-specific instructions. On any Job, fields may be renamed/removed or
  added with independent overrides; master edits do not overwrite existing job
  values. A required field must be completed before status can change to
  Completed. Older milestone records are preserved in a separate legacy view.
- **Real visual rainbow picker:** Drag across a visible hue gradient and a
  2-D light/dark saturation palette. Named one-tap color presets and optional
  exact hexadecimal entry remain; **no RGB channel sliders**.
- **Estimates and invoices:** Headings and exported HTML no longer display
  “Draft”. Internal financial limitations remain: no legally issued immutable
  invoice numbering, automated taxes or payment settlement verification.
- **Modernized UI:** Six two-column workspace tabs (Home, Jobs, Calendar,
  Contacts, Customers, Business), rounder controls, stronger text contrast and a
  Home overview showing today/upcoming jobs, customers, independent contacts,
  sent estimates, job value, payments, open balance and next appointment.
- **Calendar recovery path:** Job > **Add this job to Calendar app** opens the
  Android calendar's normal event editor prefilled with title, site, start/end
  and short notes. The user picks a Google/device calendar and explicitly
  presses Save. This uses the same user-confirmed handoff pattern as the
  working dumpster calendar reminder. Automatic one-way account sync remains
  under **Advanced calendar settings (experimental)** and is **no longer
  triggered automatically by opening Schedule**. Manual handoff is **not
  two-way automatic synchronization** and may create duplicates if repeated.

### Manual test path (synthetic customers only)

1. Open Contacts, select **Import ALL phone contacts** and grant permission.
   Confirm the Contacts count increases but **Customers count does not**.
2. Open a contact and explicitly promote it to a customer. Confirm it appears
   in Customers and remains in Contacts.
3. Business > Customize master job fields: rename Dumpster delivered to
   Site inspection, add a required field, and create a new job. Change a
   checkbox and reopen the job to verify persistence.
4. Add or rename a field only on that job. Confirm the master template and a
   second job remain unchanged. Try to mark the first job Complete with an
   unsatisfied required field; expect a clear validation message.
5. Pick a brand color by dragging the rainbow/2-D shade controls, without
   typing a code. Confirm the selected color persists after reopening Business.
6. Open Estimate and Invoice previews. Neither heading should say Draft.
7. Tap Add this job to Calendar app, inspect the prefilled event, choose the
   intended Google/device account and save there. Review the event in the
   calendar app. Do not use experimental bulk sync for real jobs.
8. Confirm the previously working fingerprint/PIN lock, photo import, and
   local dumpster pickup notification were not regressed.

### Open acceptance gates

- Physical Android 15 tests: permissions, import thousands of contacts, manual
  calendar event selection, all job field kinds, screen reader/touch target
  navigation, document preview/PDF quality and backup recovery.
- Unit/CI checks are not substitutes for a complete business acceptance.
- App lock protects UI access but **active on-disk CSV data is not encrypted**;
  password-protected backups are an optional separate feature.


**Maturity: In development; not a completed field-service CRM.**
**Owner:** `onnxscibroccoli/broccoli-core`, isolated `experiments/accubook/android`.
**Product acceptance contract:** [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md).
**Base experimental APK:** draft PR #81. **Integrated development:** draft PR #82. **Workflow pass:** draft PR #84.

## Purpose

Accubook is a sovereign, accessible, usable CRM for small contractors and service
businesses. It must connect people, properties, schedules, work, evidence,
estimates, invoices, payments and operations without imposing a hosted backend or
runtime AI dependency. A passing APK compilation does not establish feature
completeness, accessibility or data-recovery readiness.

## New integrated workflow branch (draft PR #84, 2026-11-06)

Branch: `feat/accubook-workflows-20261106`. **Experimental only; no device acceptance.**
This branch adds connected workflows to the PR #82 foundation:

- **New job -> new customer** directly inside the job flow, and quick customer
  selection. The job form does not silently default the appointment date.
- **Schedule** with native calendar picker **and typed ISO date**, native clock
  pickers **and typed 24-hour start/end**, appointment notes, color coding,
  day/week/month daybook, drag/drop jobs onto another date with a documented
  accessible calendar-based alternative.
- **Customer preferences**: independent checkboxes for call, SMS, email, and a
  customer color. These are preferences, **not** marketing consent.
- **Bulk phone contact import**: Android READ_CONTACTS is requested only when
  explicitly choosing bulk import. User selects checked entries (up to 250 shown)
  and duplicates are skipped by matching normalized phone/email. Permission may
  remain granted until revoked in Android settings. Existing one-contact Android
  system picker remains available without READ_CONTACTS.
- **Bulk media and file import**: SAF chooses up to 40 files in a batch;
  any file MIME may be privately attached (25 MB max each), then exported or
  removed. Media photo import also supports multiple images. File bytes are
  never executed as code.
- **Quote and invoice visual editor**: a local HTML paper preview with directly
  editable message and closing sections, limited text-format toolbar, live
  customer/billing-line merge, brand palette and chosen company logo. Reuse
  the saved layout as a **default template** for new jobs. Print through
  Android's native print flow and select **Save as PDF**. This editor is a
  limited in-app WYSIWYG document composer, **not** a complete word processor.
- **Quotes**: preview/share text through an explicitly chosen external app
  (no proof of delivery) and manually mark Quote sent via checkbox.
- **Payments**: manually record payment receipts by Cash, Check, Cash App,
  PayPal, Bank Transfer or Other with date, reference and note. Dashboard
  displays separate method-based ledger totals. No live payment-provider
  integration, receipt guarantee, refunds, tax engine or reconciliation.
- **Fictional test business**: explicitly chosen seed of three test customers,
  jobs, colored appointments, quote flag, invoice rows and example payments,
  without overwriting other data.

**Operational dependencies:** None for core offline features. `READ_CONTACTS`
is used exclusively for opt-in multi-selection; print/save to PDF and
document picking use Android framework interactions. No INTERNET permission.

### New prototype acceptance walkthrough (fictional data only)

1. From Home choose **+ Schedule job / create customer**. Select **Create new
   customer**, save contact preferences, then return directly to job creation.
2. Type an ISO date or open the calendar, use both clock buttons for start/end,
   select job color and add a short daybook note. Save. Confirm it appears in
   Schedule with its color and time. Long-press and drag onto another day or
   open the job and use **Reschedule** (screen-reader alternative).
3. From Business, enter example business branding and choose a small PNG/JPEG
   logo. In a job add invoice lines. Open the **Quote editor**, edit message/
   footer inline, save it as the default template, preview, and select
   **Print / Save as PDF** using the native print destination.
4. Share quote text explicitly, then check **Quote sent** only if actually sent.
   Record a fictional check/cash receipt and verify the correct method ledger.
5. Import several test files, save a copy, and verify backup ZIP export/restore
   to a disposable workspace. Avoid real contacts until migrations are accepted.
6. From Business choose **Create fictional test business data** to exercise
   three customers/jobs and the dashboard. Running twice inserts duplicates
   because it deliberately does not overwrite existing sample records.

### Still blocked

Device-level user journey acceptance, TalkBack/switch/large-text and PDF print
validation, conflict detection, crew assignment, recurring bookings, tax rules,
payment refunds/settlement and audited cross-file transaction recovery. The UI
includes accessible rescheduling; drag-and-drop **must not** be the sole method.
The App's private records are deleted on uninstall. Export a backup before any
reinstallation, and remember CI debug builds may use different signing keys.

## Currently implemented in this child development branch

- Home, Customers and accessible Day/Week/Month date agenda with explicit navigation.
- Tap a customer to view name, phone, email, billing address and linked job history.
  Search customers by name, phone, email or city; edit customer details.
- Permissionless system contact picker for **one phone entry** at a time; prefill
  name and phone in the normal editable registration form. Other phone numbers,
  email addresses and bulk deduplication are not imported.
- Explicit phone dialer, text and email handoff to the device's installed apps.
- Job to customer navigation; scheduling date and job status editing, field notes and site instructions, and separately tracked material requests (Requested/Ordered/Delivered/Used/Cancelled).
- Add/edit/remove draft line items and rederive totals from canonical item CSV.
- Choose a JPEG/PNG/WebP from a system picker; copy at most 25 MB into the
  private job folder, show a bounded preview and confirm photo removal.
- Offline ZIP workspace export through Android Storage Access Framework.
- **New:** bounded ZIP import, structural integrity/foreign-key/billing checks,
  ZIP traversal and oversized-entry defense, staged directory swap, preservation
  of prior workspace as a rollback snapshot and crash recovery between swaps.
  Explicit revert and cleanup controls. These paths require device testing
  before they are approved for real customer data.
- No `INTERNET`, root, broad storage, or Shizuku privileges; `READ_CONTACTS` is optional and consent-gated for multi-import.
  No runtime AI calls, cloud database, service worker or telemetry.

## Prototype smoke walkthrough (fictional data only)

1. Install the `app-debug.apk` from the **exact successful branch-head** GitHub
   Actions artifact, or use the extracted APK supplied alongside this branch.
2. Open Accubook. Choose **Try with a sample customer and job**, then
   **Create sample**; this inserts an explicitly fictional customer, tomorrow's
   gutter job, two draft billing lines and a field note. It does not call a
   remote service or import phone contacts.
3. The app opens that customer's profile. Confirm phone/email/address,
   locate **Job history** and tap the linked demo gutter job.
4. In job details, test **Reschedule date**, **Change job status**,
   **Edit field notes**, **Request materials**, and **Add photo from device**.
   Use only sample images (no real customer/site evidence).
5. Open **Schedule**, switch Day/Week/Month and navigate between dates.
   Reopen the rescheduled job to confirm the date.
6. Export a ZIP backup to a user-chosen location and verify the file exists.
   Backup restore is available but remains under Android-device acceptance.
7. Relaunch the app and confirm the demo customer, job and edits persist.

The Android 15 emulator flow is documented in `scripts/emulator-smoke.sh`,
executed by `accubook-emulator-smoke.yml`. A passing emulator UI smoke
still does not replace the physical-device/TalkBack acceptance gate.

**Debug signing warning:** different CI runners may generate different
debug signing certificates. If Android refuses an upgrade, first export a
workspace ZIP from the installed build. Uninstalling removes app-private
records. Do not enter real customer data into engineering previews.

## Safety limits

- **Do not enter real customer information until restore and upgrades are device
  validated.** App-private records are lost on uninstall.
- Restoring replaces the current workspace **after** ZIP validation. The previous
  workspace remains in a sibling app-private rollback directory until the user
  explicitly discards it. Do not discard it before verifying the import and
  exporting another independent backup.
- CRC checks, filename validation, referential integrity and staged swapping
  reduce risk but do not yet prove database-grade transactions or full crash safety
  across all possible storage failures. Backups can contain sensitive customer
  information; keep them private and encrypt user-selected copies where needed.
- Canonical schedule date and status reside in `master_data/jobs.csv`; the
  historical `job_details.json` is **not authoritative** and may still contain
  the date at job creation. This duplicated field needs migration cleanup.
- Multi-file customer/job creation, receipt handling, status history, time
  windows, teams, recurring jobs, estimates, taxes, payments and production
  accounting remain unfinished.
- The job photo implementation uses the system image chooser, not camera capture
  or before/after classification; no geotag/metadata editing or album sorting.
- Contact import intentionally uses per-selection access, not whole-address-book
  permission; field-by-field import enhancements remain a release requirement.

## Build and inspect

Current development branch: `feat/accubook-integrated-crm-20261106`.
Android SDK 35, JDK 17 and Gradle 8.11.1:

```sh
cd experiments/accubook/android
gradle :app:assembleDebug --no-daemon
```

Standalone JVM validations (no Android dependencies):

```sh
cd experiments/accubook/android
mkdir -p build/csv-test
javac -d build/csv-test \
  app/src/main/java/com/accubook/crm/CsvCodec.java \
  app/src/main/java/com/accubook/crm/BackupArchive.java \
  app/src/test/java/com/accubook/crm/CsvCodecSmoke.java \
  app/src/test/java/com/accubook/crm/BackupArchiveSmoke.java
java -cp build/csv-test com.accubook.crm.CsvCodecSmoke
java -cp build/csv-test com.accubook.crm.BackupArchiveSmoke
```

The `Accubook Android Debug APK` workflow compiles the APK, checks debug signing,
records SHA-256 and executes the standalone regression tests. **A successful run
does not confer Android device acceptance**. Manual testing must include
TalkBack and large fonts, contact-picker cancellation, scheduled-date changes,
photos, and repeated backup/restore/revert with destructive corruption fixtures.

## Product scope and release gate

See [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) for complete acceptance matrix,
end-to-end interaction contracts, entity graph and G1–G8 release requirements.
The next APK should not be handed over as a **complete** application until all
critical workflows, independent validation and acceptance gates pass.

## Upstream boundaries

Accubook's customer data stays separate from the Broccoli Core governor/event-bus,
Grasshopper/Helix and privileged rish transports. Future adapters must be
provider-agnostic, opt-in and explicitly permissioned. Synchronization to an
unconfirmed Google Drive folder is not performed.
