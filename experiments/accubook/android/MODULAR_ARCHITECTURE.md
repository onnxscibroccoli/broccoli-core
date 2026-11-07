# Accubook modular architecture and migration contract

## Inventory implementation — one independent vertical slice

`StockLedger` is a pure Java event model that derives company, job-site
and tool balances from a single immutable movement sequence. Every event
has a stable ID, item ID, UTC time, action, source/destination, quantity and
optional explanation; count corrections require an explanation. Validation
rejects duplicates, unknown items, unknown jobs, invalid action routes,
negative balances and fractional tools.

`InventoryStore` persists an item catalog separately and writes each
movement as **one atomic append** to `master_data/inventory_movements.csv`;
one event represents both debit and credit so transfers cannot commit only
half the balance. `InventoryActivity` is a standalone UI component rather
than another large business tab. It displays a simple Company/Job/Tool view
and common actions, with optional per-job entry from Materials.
`BackupArchive` validates these CSVs on restore, preserving older workspaces
without inventory files. `BusinessSetupProfile` uses version 2 of its CSV
schema with backward-compatible version 1 reads; Inventory remains off
until explicitly enabled.

**Not yet:** inventory cost/cost-of-goods accounting, procurement, purchase
orders, automated Material Request inventory postings, serial numbers,
advanced location entities, barcode scanning, crew sync, warehouse reorder
points, stock audit exports, automated material suggestions. Every feature
must be verified independently before a maturity claim.


## Incremental migration implementation

`LegacyContactsCsv` is the first standalone parser module. It has strict
size/row/column limits and deterministic SHA-256-derived source identifiers;
`LegacyContactsImportActivity` owns the visual mapping and approval; existing
`ContactDirectory.importBatch` provides the single atomic contact write.
No customer creation, job mutation, credential collection or network calls.
The pure-JVM smoke test exercises ambiguous mapping and malformed files.

This is **only contact CSV import**, not a generalized cross-CRM migration
or a safe bulk update transaction spanning customers/jobs/invoices.
Extending the migration architecture must preserve staging, mapping review,
audit summaries, cancellation/rollback and per-adapter fixture validation
before any new entity type is included.


**Maturity:** architecture decisions plus one implemented vertical slice
(first-run questionnaire). **Last reviewed:** 2026-11-07. **Scope:**
`experiments/accubook/android`, not all of Broccoli Core.

## The product contract

The smallest useful workflow is **find customer → open job → record work →
create/send invoice → mark payment and next visit**. A one-person gutter
business should not have to configure crews, route tracking or an accounting
integration. The owner can customize the default job fields and pricebook
through the UI. No subscription, account, runtime LLM, online server, or
external permission is required to use the existing core.

### What exists (engineering preview)

- Android app with locally stored customers, independent contacts, jobs,
  custom job fields, notes, photos, pricing, recurring due-date *lists*,
  estimates/invoices, manual receipts, change orders and signatures, and
  portable backups. These features have different verification levels; see
  the README and `PRODUCT_REQUIREMENTS.md`.
- `BusinessSetupProfile` is a versioned pure Java model; `BusinessSetupStore`
  writes `templates/business_setup.csv` atomically; `BusinessSetupActivity`
  is a separate, accessible, offline questionnaire. `FeatureSettings`
  reads/writes these saved choices once setup is completed or skipped.
  Existing SharedPreferences choices remain the fallback for legacy users.
- `BackupArchive` allow-lists and validates the setup file during restore,
  preserving older backups without it. The added pure-JVM test validates
  roundtrips, malformed settings and restore rejection.

**Important:** Android `MainActivity.java` remains a large orchestration/UI
class. Existing feature flags hide screens but are not a complete executable
plugin system. This work must not be described as full re-modularization.

## Next bounded refactors — order matters

1. **Split business operations into independent vertical slices.** Start with
   inventory, then the import-preview workflow. Each slice owns a model,
   file schema/migrations, bounded repository, UI, help, rollback, and tests.
   Keep the existing core storage APIs until migration is independently tested.
2. **Inventory as a transaction ledger, not three unrelated totals.**
   Item catalog (material/tool), locations (warehouse/vehicle/job site),
   movements (receive/transfer/use/return/adjust), reservations and tool
   checkout. Display three simple views but preserve a single audit history.
   Reject negative quantities and repeated movement IDs; allow explicit
   adjustments with a reason. Vendor APIs remain optional adapters.
3. **Editable trade modules.** Versioned module manifests declare default
   fields, view sections, feature switches, migration hooks, compatibility,
   visibility and export coverage. Never execute arbitrary imported scripts
   from a CSV, ZIP or a downloaded `AGENTS.md` file. Each module must have
   a testable data contract, an owner-controlled enabled state, and an
   accessible long-press *and* visible action menu.
4. **Finance:** reconcile posted change orders and original estimates;
   immutable numbered invoices, tax handling rules and an auditable payment
   ledger are prerequisites for formal accounting integration.
5. **Search and document UX:** one search input; selectable unpaid-invoice
   bundle as PDF/ZIP; consistent edit/undo controls and printable visit slips.

## Safe CRM-to-CRM migration architecture (not implemented yet)

A migration is a **dry-run first** import, never an unreviewed merge.

1. Import selected local CSV/JSON/ZIP files through Android's system picker.
   Do not request raw access to third-party cloud accounts by default.
2. Parse strict bounded UTF-8, with CSV quoting/headers and ZIP traversal
   protections. Reject executable entries, unknown file types, oversized
   files, inconsistent dates and non-finite/invalid money.
3. Infer field maps and display a side-by-side **preview** of source columns,
   destination fields, sample rows, unmatched references and duplicates.
   Require explicit user correction for uncertain matches. Contacts must not
   silently become customers.
4. Stage normalized records in a temporary workspace, validate referential
   integrity and compute counts/checksums. Preserve external source IDs and
   provide a conflict report. Never overwrite existing records on name alone.
5. Obtain explicit owner confirmation of exact counts, mapping and destination.
   Commit with a verified rollback snapshot; cancel or failure leaves
   original data untouched. Produce a portable migration report.
6. Integrate first one format with fixture-based tests, then add named-vendor
   adapters as isolated packages. Distinguish **export data import** from
   an authorized API-based direct import.

A future LLM may *suggest* a mapping offline or through an explicit, consented
user action, but the runtime importer must deterministically validate every
field without relying on an AI provider.

## Crew sharing and encryption — engineering constraints

**Not yet implemented.** A worker invite must not be a perpetual bearer key
sent in plaintext. Proposed design: short-lived single-use pairing invitation;
device-held identity keys; authenticated end-to-end encryption; least-privilege
job subscriptions; monotonic replay protection; offline change queue; explicit
conflict resolution and owner revocation. A service or relay may be necessary
across mobile networks/NAT. LAN/Wi-Fi Direct/Bluetooth can be optional local
transports. Do not assume RCS exposes arbitrary end-to-end IP sockets to
third-party apps. Current AndroidManifest intentionally has **no INTERNET**
permission. No worker syncing is currently claimed.

## Voluntary support and business model

The app is designed to remain useful with **zero ads and zero donations**.
No ads or donation processors are integrated today. A future advertising
module must default **off**, be fully dismissible without payment, never
alter customer/workflow data, and not silently export customer/contact/job
details. Voluntary Cash App/Google Play contributions are a separate UI
surface with no functional unlocks or account requirement. Provider/platform
rules will be reviewed before adding payment links.

## Release evidence

A passing Gradle build or JVM suite is not a completed field acceptance.
Require exact-HEAD CI, on-device Android 15 smoke tests, TalkBack/large text,
locale/timezone, clean install vs upgrade, input validation, ZIP rollback,
offline mode and records-preservation tests. Mark uncertain features
*experimental* rather than claiming production equivalence. For each
module, update the README, user guide, data schema and verification evidence.

## For AI development agents

Before editing a module: read this contract, README and its current test
fixtures. Change one vertical slice, preserve existing workspace compatibility,
add negative tests, run the offline JVM suite and Android build, verify exact
commit CI, then open a **draft** stacked PR. Do not merge or publish a signed
release without independent device acceptance. When collaborating with the
Broccoli/Grok Governor or other AI developers, exchange module boundaries,
file schema versions, test results and exact commit SHAs; never treat a tool
notification as device verification.
