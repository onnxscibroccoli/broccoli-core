# Accubook — offline-first field-service CRM (engineering preview)

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
