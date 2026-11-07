# Accubook — field-service CRM product contract

**Maturity:** In development. **Audience:** owner-operators, estimators, production managers,
dispatchers, office staff, and field crews in roofing, exterior trades, repair, maintenance,
and other small service businesses. This is a product acceptance contract, NOT a release claim.

## Product rule

An APK that compiles is not a finished CRM. No final debug handoff or production launch claim
until the following workflows work end to end on a physical Android device, including
TalkBack, data recovery, and actual contractor use cases. A single isolated feature does not
count as finished if the related customer/job/estimate/invoice flow is disconnected.

## Foundation — nonnegotiable

- Offline-first: read, search, edit and create data without an account, network or server.
- Sovereign data: portable, versioned exports and proven restore; no secret outbound telemetry.
- No root, Shizuku or privileged access. Use documented Android APIs with explicit SAF/contact
  picker/media chooser interactions. No blanket contact or media scraping.
- No runtime AI or API subscription. No hosted dependency for core workflows.
- Native accessibility: visible labels, headings, predictable Back, 48dp+ touch targets, dynamic
  font resizing, high contrast, full keyboard/switch/TalkBack operation, clear errors and undo
  or explicit confirmation before destructive steps. Test against WCAG 2.2 AA where applicable.
- Integrity: stable record IDs, transactional persistence, migrations, rollback and fault tests.
  No silent corrupt-file resets, silent orphan deletion, or guessed financial values.

## Required navigation and relationships

Home / Customers / Schedule / Work / Estimates / Invoices / Business / Settings.
All records must be reachable in at most a few obvious taps without memorizing IDs.

- Customer -> full contact card -> call/text/email -> service properties -> all jobs,
  estimates, invoices, notes, photos, communications and payment history.
- Job -> parent customer, site, appointment(s), assigned crews, field notes / gate codes / material requests, checklists, evidence,
  costs, estimates, change orders, invoice(s) and activity history.
- Date/time calendar -> job -> customer. Changes propagate everywhere without duplication.
- Global search -> customers, jobs, addresses, invoices and searchable notes.
- Always show current status, last edit and meaningful next action. Empty states provide
  a primary action and explain why the page is empty.

## Functional acceptance matrix

| Area | Complete behavior expected | State on this development branch |
| --- | --- | --- |
| Customers | Create/edit/archive/merge, multi-contact, phone/email/address, notes, tags, lead source, searchable job history | **Partial:** customer detail, edit, search, job history, preferred method checkboxes and color; no archive/merge/multi-contact |
| Phone import | Explicit single/bulk import with dedupe, multi-number/email, cancel/consent handling | **Partial:** single-contact picker plus opt-in READ_CONTACTS multi-checklist (first 250 entries, basic phone/email dedupe); no complete import history/merge |
| Properties | Multiple service sites per customer, property/equipment history, site photos | Not implemented; job site fields exist |
| Leads / requests | Lead intake, stage, notes, follow-ups and quote conversion | **Partial:** customer/active jobs/quote/payment method dashboard, no full A/R/profit reports |
| Estimates | Templates, grouped labor/material, alternatives, taxes, approval, revision log | Not implemented |
| Jobs | Prospect→Quoted→Approved→Scheduled→In Progress→Completed→Invoiced→Paid (payment-backed), field notes/gate codes/material requests, assignable and recurring work, change orders, attachments | **Partial:** add job, status/date change, field notes, materials requests, photo import and basic line items |
| Scheduler | Day/week/month calendar, date and time slots, timezone, crews, capacity/conflicts, drag or accessible reschedule | **Partial:** day/week/month daybook, native calendar/clock and typed date/time, notes/colors, basic drag-to-date plus accessible alternative; no crew or conflict detection |
| Crew operations | Personnel, assignments, check-in/out, on-site tracking, work orders | Not implemented |
| Photo evidence | Camera, gallery, metadata, annotation, before/after, album, export, deletion | **Partial:** private JPEG/PNG/WebP attachment, bulk photo selection, preview, remove; no camera/annotation |
| Pricebook | Searchable service/material catalog, units, rates, templates | Initial CSV container only |
| Costs | Expenses, purchase orders, receipts, labor cost and profitability | Initial CSV container only |
| Invoices | Numbering, estimates->invoices, adjustments, tax, print-ready HTML and PDF with optional evidence photos, email, balance, due dates | **Partial:** editable lines, offline WYSIWYG message/footer, reusable default template, brand/logo, HTML preview, native Print/Save as PDF; no tax/settlement |
| Payments | Offline cash/check ledger, deposits, partial payments, refunds, reconciliation, audit | **Partial:** user-entered per-job cash/check/Cash App/PayPal/Bank Transfer/Other receipts, derived method totals; no card processing, refund/reconciliation |
| Communications | Explicit dial/SMS/email via installed apps, notes and logged activity | **Partial:** dial/text/email handoff, share quote text, manual Quote sent checkbox, no delivery receipts/history |
| Reporting | A/R aging, pipeline, jobs by status, revenue/cost/profit, CSV exports | Not implemented |
| Backup/restore | Verified, safe, versioned backup AND restore; migration and corruption tests | **Partial / not accepted:** staged ZIP restore, structural validation, retained rollback, JVM fault/abuse smoke. Real-device and power-loss testing pending |
| Desktop/iOS | Portable domain, parity and user-controlled interoperability | Not implemented |
| Accessibility | Automated and manual testing with TalkBack, Switch Access and font scaling | **Unverified** |
| Installation | Android 8+ device install, upgrade, rollback/data-preservation testing | **Unverified** |
| Release | Key custody, migration rehearsal, privacy/security review, owner acceptance | Not approved |

## New in opt-in development branch `feat/accubook-workflows-20261106`

- Job creation now links to **Create new customer** and returns to scheduling.
  Date is empty until explicitly chosen or typed; native calendar and clock
  fields have keyboard alternatives. Time zones/overnight visits remain unmodeled.
- Daybook includes colored appointment blocks, notes, and drag-to-date; a
  keyboard/screen-reader-accessible Reschedule dialog is mandatory.
- Customer preferred Call/SMS/Email checkboxes, color selection, optional
  opt-in bulk contact selection; READ_CONTACTS is granted/denied by Android.
- Mixed-format attachments: arbitrary MIME formats copied to app-private
  storage through user-selected SAF; max 25 MB each/40 per batch; export copies
  through SAF. No preview/execution of unknown binary content.
- Quote status checkbox is a **manual self-report**, not proof of customer
  receipt. Quotes and draft invoices use canonical job line items and optional
  business logo, HTML editing regions and native system Print/Save as PDF.
- Payments are offline **manual** ledger entries, not payment acceptance or
  external-provider settlement. Refunds, reversals and correction controls
  remain blockers before trusting production accounting.
- Default rich text template is user-controlled and locally stored. On Android,
  WYSIWYG formatting, PDF print and TalkBack navigation still require device
  acceptance (no green compilation substitutes).
- Fictional test company and three jobs/ledgers may be inserted on demand;
  no real client data and no background imports.

## Interaction design contracts

1. From the Customers list: tap a named customer; their contact details, actions and
   complete job history are visible. Add another job from the profile and return here.
2. From Schedule: tap a dated job, see the linked customer and site, change status/date;
   return to the agenda and verify the move. Later: times/crew collision detection.
3. From a job: create/edit field instructions and material requests; attach a photo from an explicit system chooser, see its thumbnail,
   remove it only after confirmation; backup retains the image.
4. From a job: add/edit/delete a billing row; invoice totals reflect canonical rows.
5. Phone import: pick one contact; see the selected name and phone in an editable
   registration form; cancelling never creates a record.
6. From ANY relevant screen: follow labeled Back/navigation; state and user data persist
   across process restart, orientation changes, failure and upgrades.
7. On a corrupt workspace: present an actionable recovery path, never initialize over
   the only surviving copy. Backup restore must be proven before real customer data.
8. At no point should a successful CI build or exported HTML be described as
   operational acceptance, paid invoice, payment settlement, or production quality.

## Domain architecture direction

- Separate domain model from Android widgets. Keep portable human-inspectable
  UTF-8 CSV/JSON/Markdown/HTML, master indexes and per-customer/job folders as the
  **canonical workspace**, as specified in the original architecture. Add a
  versioned write-ahead journal for multi-file transactions and crash replay;
  in-memory or SQLite indexes may accelerate search only as rebuildable caches.
  Never move authoritative records into an opaque database without an explicit
  product architecture decision.
- Entity relationships: Customer -> Contact, Property -> Job -> Visit -> Crew Assignment;
  Job -> Checklist/Attachment/TimeEntry/Expense; Estimate -> ChangeOrder -> Invoice
  -> PaymentLedgerEntry. Use IDs and referential constraints; preserve audit events.
- Use explicit migrations with tested forward/back compatibility and fixture backups.
- Consider event-driven projection updates (domain events, idempotent handlers) without
  coupling customer data to Broccoli Core governor or remote control code.
- External calendar sync, online payments, team multi-device sync and customer portals
  inherently need external capabilities. Keep them **optional adapters** and never
  suggest that fully shared collaboration can work offline on isolated devices.
- Import/export is user-initiated, reviewable and reversible. No background upload.

## Launch gates (must ALL be satisfied)

G1: every acceptance-matrix core workflow implemented end-to-end; no dead navigation.
G2: destructive, failed and cancelled operations preserve user data; crash/fault injection pass.
G3: on-device test with Android 15 (including Samsung A14 where available) and Android 8 baseline.
G4: accessibility audit with TalkBack, Switch Access, large text, keyboard, landscape,
    contrast, focus order, form feedback and no gesture-only operations.
G5: backup/restore verified with live upgrade, corrupt files, large photos, ZIP abuse fixtures,
    migration and replay/rollback tests; restore never silently overwrites.
G6: monetary correctness: tax rules, rounding, invoice states, partial payments and backups.
G7: security/privacy review, permission disclosure, safe share targets and no INTERNET grant.
G8: independently reviewed signed release candidate, reproducible build and owner sign-off.

Only after G1–G8 pass may the next APK be called **complete**. Until then use
"engineering build" and refrain from returning a final application download.

## Related verification

- Existing PR #81: Android compilation, signature and CSV codec only.
- This branch: integrated navigation/domain edits awaiting fresh CI and device validation.
- Reference patterns: Jobber and Housecall Pro service workflows, interpreted as functional
  requirements, not permission to copy proprietary UI/brand/assets.
