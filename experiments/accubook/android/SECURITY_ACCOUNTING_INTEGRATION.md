# Accubook integrated CRM — implementation and acceptance contract

Lifecycle: **In Development / Not Production Verified**
Branch: `feat/accubook-security-accounting-ux-20261106`
Related development: draft PR #84 and this incremental stacked PR.
Verification policy: only call capabilities CI Verified after tests execute successfully
against the exact head; do not claim device usability from an APK build alone.

## Architecture and privacy boundary

- Source of truth: app-private `Accubook Workspace` tree with bounded CSV files,
  job/customer directories and explicitly user-picked SAF files.
- No direct `INTERNET` permission, runtime AI calls, root, Shizuku, or vendor
  subscription. No upload of customers, locations, estimates or financial data by
  Accubook code. User-initiated external apps (calendar, maps, email, accounting)
  may disclose only their selected information subject to their own policies.
- **Native app unlock**: optional Android enrolled biometric or device credential
  (device PIN/pattern/password); cannot bypass secure device setup. Screenshot
  protection while enabled. This is app access control, **NOT encryption at rest**.
- **Encrypted backup**: user-requested AES-256-GCM `ACBK2` portable archive,
  PBKDF2-HMAC-SHA256, 210k iterations, random salt/nonce, authenticated before
  staged ZIP restoration. The passphrase is never saved. Lost passphrase means
  the encrypted archive cannot be recovered. Plaintext working CSV files and
  intentionally unencrypted ZIP backups still exist. Decryption transiently
  uses a private cache file that is cleaned after use, not a guarantee against
  filesystem forensics or full-disk extraction.
- Release blocker: move all active data to authenticated encryption at rest,
  bound to Android Keystore/device lock, preserving portable passphrase-protected
  backup recovery and supporting safe key rotation/migration.

## User stories now implemented in the development branch

| Domain | Behavior | Known limitations |
| --- | --- | --- |
| Contacts | Whole authorized address-book browse with search, persistent selection across 60-item pages and dedupe | Large address-book usability/device test pending; current import uses selected phone/email |
| Terminology | Customer-facing Estimate language in primary UI/documents; internal legacy identifiers may remain for migration | Audit all historic docs and screens before production |
| Documents | Deterministic friendly `EST-XXXX-XXXX-XXXX` / `INV-XXXX-XXXX-XXXX` references and merged line items | These are not issued legal sequential tax invoice numbers; collision test and immutable issued state pending |
| Photos/files | Original-format JPEG, PNG, WebP, HEIC/HEIF, AVIF, GIF, BMP, TIFF, DNG and image picker MIME; private file attachments | Preview codec depends on Android support; 25MB limit, no arbitrary executable preview |
| Saving | Atomic per-file writes, validation error keeps form open, authenticated ZIP rollback | Cross-file journal, crash injection and transaction reconciliation still missing |
| Expenses | User-entered category, description, date, amount, confirmed delete | No chart-of-accounts or immutable double-entry corrections |
| CSV exports | User-selectable ZIP sections for customers, jobs, line items, payments, expenses, timesheets | Manual QuickBooks column mapping; no QuickBooks account connection or automatic tax calculations |
| Calendar UX | Native month grid with colored counts, day/week/month agenda and drag/date edit | Accessibility manual tests and crew conflict detection pending |
| Backup | Export ZIP, prominent restore/revert; encrypted ACBK2 export/restore | Test full power-fail restore, key loss and low-memory failure |
| Branding | Default new-profile Jules Gutter Cleaning, explicit apply to saved workspaces, RGB+hex color controls | Owner confirmation needed on old workspaces to avoid overwriting intentional customization |
| Billing ergonomics | Catalog inserts to canonical line items, quantity +/- confirmation, estimate-sent confirmation | Financial approval/reversal policy and issued-invoice locking pending |
| Trade templates | Editable any-trade service/material catalog, markup per default or job, custom job milestones, vendor/crew/delivery notes | Template-pack versioning, per-trade permissions/roles pending |
| Clock in/out | Multiple named worker clocks on one device, UTC instants and decimal-hours export | Not true authenticated multiuser or multi-device collaboration; break/overtime/payroll rules pending |
| GPS/maps | Explicit foreground-only GPS point logging, opt-in GPX export, browser handoff to OpenStreetMap after location-sharing confirmation | No full map renderer or online routing API; GPS collection stops when app backgrounded |
| Calendar sync | Explicit READ/WRITE_CALENDAR opt-in and selected writable Android calendar; reconciles jobs by tag; local Google account sync handled by installed calendar | Not a first-party Google Calendar OAuth client; no guaranteed background sync, conflict reconciliation, shared-account permissions or automatic deletion on opt-out |
| Pickup reminders | User-scheduled local inexact alarm; permission-gated notifications; rearm on device boot | Android may delay notifications; no exact timing/SLA and no fully automatic vendor dispatch |
| Supplier pricing | Owner-approved price sheets from Lansing/QXO/SRS/Manual with timestamp, bounded all-or-nothing import; catalog item cost/markup | **No live supplier API requests.** Contract, credentials and approved API schemas are required before implementing remote connectors |

## Supplier integration adapter contract

External supplier connectors should only be added after contract review.
QXO publishes official account-gated Pricing, Product, Account, Invoice and Order
APIs (https://www.qxo.com/customapi and https://go.qxo.com/qxoapi).
Lansing offers LansingNOW online account/pricing, but a supported developer
API contract is not established. SRS Distribution has partner-specific Roof
Hub integrations (including JobNimbus), not established general open API
credentials. Do **not** scrape, reverse-engineer private endpoints, bundle
credentials, or silently turn on Android INTERNET access.

A future supplier connector must satisfy:

1. Explicit owner consent to share SKU, branch/account, approximate location.
2. Authorized published API access, scoped credentials held via Android Keystore,
   no secrets in Git or CSV; independent authentication and refresh lifecycle.
3. Source/provider, SKU, currency, unit, account/branch and timestamp required.
4. Never replace a customer-approved historical estimate rate; propose new price
   and require user approval before changed billing.
5. Offline fallback to last owner-approved catalog/price-sheet; clearly show
   **stale** and **unavailable** states. No invented stock/price availability.
6. End-to-end contract tests using vendor-provided fixtures, permission revocation,
   429/rate limits, retries, stale/partial responses, clock skew and key rotation.

## Google Calendar limitations

Android's supported `CalendarContract` provider can insert/update events
into the user-selected writable calendar once permission is granted. A device
Google account may then synchronize events to Google. This sends job titles,
addresses, scheduling dates and daybook notes off-device through the **calendar
app/account provider**, and must remain opt-in. Sync is one-way and currently
refreshes when the user opens the schedule or explicitly taps sync; it is not
guaranteed background/real-time bidirectional synchronization. Disabling
sync does not retroactively revoke already-shared events.

Calendar event ownership is validated before updating a stored event ID to
avoid overwriting unrelated calendar entries after workspace restoration.

## Production release gates (unmet)

1. Install/upgrade on Android 15 + lower supported API; test actual saved data.
2. TalkBack, keyboard, switch, 200% text scale, contrast/large lists and date picker.
3. Complete multi-contact selection >250, cancellation, duplicates and permission refusal.
4. Estimate PDF and exported report compatibility with real QuickBooks import screens.
5. Valid/invalid GIF/HEIC/AVIF, corrupt MIME, memory/25 MB boundary, bulk partial failure.
6. Crash/power-loss/fault-injection tests of all cross-file operations, restore/revert,
   concurrent import and active calendar/notification interactions.
7. Threat model of backups, main plaintext data, biometric bypass, notification privacy,
   Android OS lock changes and phone loss. Encryption-at-rest requires a separate gate.
8. Real vendor calendar/supplier contracts/credentials before any claim of live integration.
9. Manual accounting reconciliation, corrective journal, refunds, stable issued-doc number
   governance and tax-jurisdiction compliance review.
10. Human owner approval after detailed engineering reviews and a production signing plan.

## TBI-friendly manual acceptance

1. **Backup** the existing workspace before installing any engineering build.
2. In Business, verify the profile or explicitly apply Jules Gutter Cleaning.
3. Try a fictional customer and a job with a calendar date, start/end time and custom
   color. Add a catalog item and inspect the live estimate total.
4. Create a second fictional worker; clock in and out. Record a cash expense.
5. Complete a dumpster milestone, schedule a future pickup reminder and inspect
   its local notification permissions.
6. On a disposable workspace, export password-encrypted backup and restore it.
7. Optional: allow a test calendar, explicitly select its destination account,
   reconcile once, and inspect event title/site/time. Never use a real customer
   unless account exposure is accepted.
8. If any data is missing, do not uninstall; retain current files and share
   anonymized logs/screenshots for triage.

**No production claim:** an APK compiles when Android javac and unit checks pass;
it is not accepted as secure, accessible, accurate accounting software until the
release gates above have independent evidence.
