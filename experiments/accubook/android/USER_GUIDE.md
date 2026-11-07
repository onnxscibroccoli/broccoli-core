# Accubook — Point, tap, and get the job done

**State:** Engineering preview, November 7, 2026. This guide separates working features from planned ones. The active workspace is on your device. Back up before uninstalling, restoring, or testing updates.

## Only three things to remember

**Customer → Job → Work → Invoice.**

1. Open **Customers → Add customer**. A name is sufficient to start.
2. Open that customer → **New job**. Enter the work and date.
3. Open the job. Use the **Photos, Notes, Materials, Money, Checklist, Schedule** sections; you do not need to fill everything out.
4. **Photos** → Import multiple photos. Long-press or tap the photo action menu to preview, move or remove them.
5. **Notes** → Write what happened in plain language. No mandatory drop-down.
6. **Money** → Add labor, material or discount. Type the work description. Matching local catalog items appear as *optional* rate suggestions. Save your own description and rate whenever you want.
7. **Invoice** → Preview and print or choose Android Print → Save as PDF. Recording a payment is separate from issuing an invoice.

**That is enough to run a simple job.** Add more modules only as needed.

## When the work changes

1. Job → **Money → New change order**.
2. Describe the added work and add lines. The amount shown is **the change**, not a new estimate.
3. Review the total with the customer. Enter their printed name; let them sign the phone screen with a finger or stylus.
4. After acknowledgment, the order and its lines are locked against edits.
5. Tap **Add to invoice** only after checking the approval. The invoice line has a stable change-order reference; retrying an interrupted insertion skips lines already present.

The local signature PNG, timestamp, and SHA-256 digest detect changes to signed records. They do **not** prove the signer's identity, constitute a PKI digital signature, or establish legal enforceability. There is no camera co-capture or standalone change-order PDF yet.

## Customize without vendor approval

| Task | Where | What happens |
| --- | --- | --- |
| Master checklist | Home → Customize job checklist | Add, edit, move up/down, require, remove. |
| One-job exceptions | Job → Checklist | Changes stay on that job. |
| Photo order | Job → Photos → action menu or long-press | Order survives restart and ZIP restore. |
| Business color/logo | Business → Edit company / Choose business logo | User-controlled. Existing branding survives unless replaced. |
| Job color | Job → Schedule editor | Rainbow picker; text labels remain. |
| Customer indicator | Customer → Contact preferences | Rainbow picker. |
| Catalog rates | Business → Services/consumables | Future invoice lines get new rates; existing ones remain. |
| Features | Business → Settings → Modules | Hide crew, catalog, worker time, GPS and experimental calendar sync without erasing data. |

Photo grid drag handles and a fully modularized UI architecture are not yet implemented.

## Reports and financial privacy

**Business → Reports → Quick PDF** makes a local summary for reading or printing. **Custom CSV ZIP** makes a selective accounting export. Choose included sections, payment methods (Cash, Check, Cash App, PayPal, Bank Transfer and Other) and expense categories individually. All methods/categories begin excluded. A jobs-only report must not silently leak payment, receipt or balance fields.

Reports do **not** constitute a reconciled general ledger, AP/AR subsystem, tax filing, or verified QuickBooks import mapping. Review CSVs before importing and use fictional data during acceptance testing.

## Calendar and due dates

Job → Materials includes local dumpster pickup reminders. Job → Schedule hands events to Android Calendar; automatic account calendar sync is optional and experimental.

**Optional repeat services:** Turn on Business → Settings → Repeat-service due dates. Open a job → Overview → Set next service due. Enter when work actually finished and how many months/miles until another service. Home shows date-due counts, plus a list to pause/resume or manually update rules. Save or print due-service slips (PDF) exports date-due reminders only. Mileage-only rules show an odometer target, not a guessed due alert. No customers are contacted and no new appointment is created automatically.

## Quick troubleshooting

| Problem | Solution |
| --- | --- |
| No catalog match | Keep typing or save your own rate; suggestions never block you. |
| Cannot sign | Enter signer name and draw in the white pad. Empty ink is rejected. |
| Cannot edit acknowledged work | Create another change order. Signed lines are deliberately immutable. |
| Billing blocked | Check status, signature evidence, and computed amount. Do not bypass with CSV edits. |
| Missing optional tool | Business → Settings → Modules. Toggle visibility; stored data remains. |
| ZIP restore fails | Keep the current workspace; it may contain invalid CSV relationships or signed evidence. Restore a prior *verified* backup. |
| Wrong PDF/CSV fields | Cancel and reselect sections, methods and categories. |
| Need TalkBack | Android accessibility settings; visible action menus also work without long-press. |

## Expansion: build a trade template that fits the job

Start from the simple pattern: customer → site/job → notes/photos → lines → document. Add only the fields a worker actually uses. In Home, edit the **master checklist**; in an individual job, add only unusual requirements. Mark fields required sparingly. Use a catalog item for repeatable work and free text for exceptions. Hide irrelevant modules. Test offline, with large text, and time the workflow.

Custom VIN fields and basic month/mileage due rules are available. Structured vehicle histories, automatic repeat jobs, landscaping zones, inventory reconciliations and equipment integrations remain planned.

## Developer and maintainer map

| Source | Responsibility |
| --- | --- |
| WorkspaceStore.java | Canonical customers, jobs, invoice lines, notes, photos, atomic CSV workspace. |
| CrmWorkspace.java | Payments, expenses, branding, attachment and appointment records. |
| TradeModules.java / PricingEngine.java | Pricebook, supplier CSV, local pricing and milestones. |
| CatalogSuggestions.java | Deterministic local free-text hints; never mandatory. |
| ChangeOrders.java | Change-order lifecycle, independent lines, signature and idempotent billing. |
| ChangeOrderProof.java | Canonical content SHA-256 and exact-decimal money rules. |
| SignaturePadView.java | On-screen PNG ink; no camera, network or permissions. |
| BackupArchive.java | Staged, allowlisted, validated ZIP restore. |
| HelpTopics.java | Searchable user-facing help, available offline. |
| MainActivity.java | Visual Android screen host; extraction into components remains future work. |

### New workspace files

- Job/change_orders.csv: order ID, title, Proposed / Acknowledged / Invoiced, creation and acknowledgment times, signer, signature digest and content digest.
- Job/change_order_lines.csv: line ID, order foreign key, description, quantity, unit rate and extended amount.
- Job/change_order_signatures/CO-<lowercase hex ID>.png: actual handwritten signature.
- Both CSVs initialize together; no network dependency.
- A canonical hash binds the job ID, order ID, title, signed time, signer, signature digest, and ordered work lines. Changes invalidate verification.
- Single-file AtomicFile commits are durable; a multi-file transaction is **not** atomic. If interrupted before final acknowledgment, an orphan PNG can exist. Billing uses stable per-line suffixes to permit safe retry.

### Safe module expansion checklist

1. Choose between a core field and an opt-in module. Preserve backwards compatibility.
2. Use stable IDs, strict schema, explicit units and currency, size bounds, and AtomicFile writes.
3. Extend the backup ZIP allowlist **and** validation when adding any new file or foreign key.
4. Add regression fixtures for valid export/import, corrupt rows, duplicate IDs, interrupted writes and privacy boundaries.
5. Hide UI behind a feature toggle; never delete or migrate records just because the user hides the module.
6. Update this guide, README and the acceptance matrix, distinguishing implementation, CI validation and physical-device verification.
7. Test the same task as a solo contractor, field tech, scheduler, bookkeeper, and customer. Remove needless taps.

**Not yet production verified:** Android 15 physical signoff, signature rotation/recovery, full accessibility acceptance, separate signed change-order PDF, consented camera evidence, a persistent enterprise search index, automatic recurring job generation, automatic inventory reconciliation, supplier ordering, GL reconciliation and QuickBooks import formats.

**Design rule:** One obvious action; free text first; optional structure; editable owner settings; recoverable data; no background service dependency.


## One local search box

From **Home → Find anything**, type part of a name, phone number, address, job, invoice reference, material, PO, VIN in a custom field or note, then press Search. Results point to existing customer, contact, job or pricebook records. No search data is sent to a server. Searching requires at least two letters/digits and shows at most 80 best matches. For broad searches, add more terms.

## Printable service reminders

Check the actual date work was completed before setting a due rule. Mileage-only services need a current reading; Accubook cannot read vehicle odometers. The optional due-service PDF does not contact anyone automatically. Choosing a cloud document provider for the save destination may upload the PDF through that provider, despite Accubook itself having no INTERNET permission.

## Materials and tools — optional, simple mode

1. **Switch on:** Business → Settings → turn on **Company materials, job-site stock and tools**. A solo operator never needs to create crew accounts or request an administrator.
2. **Count stock:** Business → Company materials + tool inventory → **Add company material**. Enter a name, unit, count and cost. If you use a pricebook, **Copy a material from pricebook** pre-fills the name, unit and cost; the values remain editable. No pricebook match is required.
3. **Track delivery:** Open a job → Materials → **Record delivered / used / returned material**. Enter what happened, quantity, and choose its status with a visible radio button. Edit or remove a mistaken entry directly.
4. **Track equipment:** Business → inventory → **Add tool**. At a job, choose **Check out an available company tool** and tap the tool name. Use **Return tool to company** at the job or in Business. Available, checked-out and maintenance states are mutually exclusive.
5. **Back up:** Business → **Create encrypted backup** before reinstalling or restoring. The stock, job-site and tool CSV files travel with the other workspace files. Imported backups reject invalid quantities, duplicate IDs and tools assigned to missing jobs.

These three lists are a manual record, **not automatic inventory reconciliation**. Marking something Delivered or Used does not reduce the company count, record an expense or invoice it. When you want to bill it, open that job → Money → **Add labor, material or discount**. Prices remain owner-controlled. Turning off the inventory switch hides the screens and retains all files.

### Developer map — inventory extension

- `InventoryRules.java`: Android-independent strict CSV headers, stable ID and numeric/status validation.
- `InventoryLayers.java`: three local lists, AtomicFile read/write and explicit tool checkout/return.
- `BackupArchive.java`: allowlists the three CSVs and rejects orphan tool links or malformed rows.
- `InventoryRulesSmoke.java` and `BackupArchiveSmoke.java`: deterministic numeric, foreign-key and ZIP roundtrip regression checks.

For another trade, rename the displayed material, use an appropriate unit (bundle, piece, foot, gallon), and edit the owner-controlled fields. Do **not** clone the app or build a mandatory supplier integration.
