# Accubook — offline-first field-service CRM (engineering preview)

**Maturity: In development; not a completed field-service CRM.**
**Owner:** `onnxscibroccoli/broccoli-core`, isolated `experiments/accubook/android`.
**Product acceptance contract:** [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md).
**Base experimental APK:** draft PR #81. **Integrated development:** draft PR #82.

## Purpose

Accubook is a sovereign, accessible, usable CRM for small contractors and service
businesses. It must connect people, properties, schedules, work, evidence,
estimates, invoices, payments and operations without imposing a hosted backend or
runtime AI dependency. A passing APK compilation does not establish feature
completeness, accessibility or data-recovery readiness.

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
- No `INTERNET`, root, broad storage, `READ_CONTACTS`, or Shizuku privileges.
  No runtime AI calls, cloud database, service worker or telemetry.

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
