# Accubook v0.5 — evidence-led field UX review

**Status:** Engineering review, not physical-device visual acceptance.
**Verified against:** source code on `feat/accubook-modular-reporting-20261107`; official
competitor mobile documentation available November 7, 2026.
**Evidence limitation:** The supplied screenshots are **brand references**, not screenshots
of the running Accubook app. A pixel-accurate side-by-side or observed tap count requires
a captured running APK and physical Android 15 test; none is claimed here.

## Product decision rule

Keep Accubook local-first, no INTERNET permission, no runtime AI subscription, no
mandatory backend, and configurable for one operator or larger teams. Copy no competitor
code, imagery or layout. Adopt a pattern **only** if it demonstrably reduces user work,
avoids incorrect entries or improves error recovery. Preserve the original workflow
unless improvement is substantiated.

| Competitor documentation / mobile behavior | Concrete useful behavior | Accubook response | Rejected complexity |
| --- | --- | --- | --- |
| [Jobber: jobs on mobile](https://help.getjobber.com/en/articles/jobs-in-the-jobber-app/) | Visit / Details / Notes separate operations; required checklists warn at job completion. | Retain required completion gate, split job into Overview, Notes, Materials, Billing, Photos and Time & route, with compact direct section navigation. | Web-configured forms as a prerequisite to editing in the field. |
| [Housecall Pro: mobile photo attachment](https://help.housecallpro.com/en/articles/10159740-capture-and-upload-photos-videos-on-mobile) | Entry to photos from job, attachment thumbnails, failed-upload recovery. | Photos has dedicated job section, bulk import already works; local photo order and small actions are additive. | Hidden cloud upload queue for ordinary local attachments. |
| [Housecall Pro: selectable invoice content](https://help.housecallpro.com/en/articles/2876243-send-an-invoice) | User can choose what an invoice preview includes and inspect before delivery. | PDF summary / ZIP export now explicitly selects tables, payment methods, expense categories; no forced Cash App ledger. | Automatic external sending, payment solicitation or accounting credentials. |
| [JobNimbus: subcontractor mobile](https://support.jobnimbus.com/how-do-i-navigate-the-mobile-app-as-a-subcontractor) | Today's Work and Upcoming Work permit fast access to job, site and photos. | Existing Home HUD and new focused job views; keep a one-tap Photos section. | Separate subcontractor app and mandatory roles for solo use. |
| [Housecall Pro: offline limits](https://help.housecallpro.com/en/articles/4747652-housecall-pro-mobile-faq) | Previously loaded job data may be read offline, but documentation does not support offline edits. | Keep native local CSV edits/backup the source of truth. | Connectivity dependency or subscription requirement. |

## Zero-friction screen inventory

| Task | Source baseline | New target behavior | Test |
| --- | --- | --- | --- |
| Open a specific job | Jobs > job card | Same parent context; default Overview; selected section preserved on edits | Switch section, edit, Back, reopen; no job jump |
| Take or import photos | In large job details | Job > Photos > Import multiple photos | 20 photos, preview, order, backup and restore |
| Update dumpster delivery | Long job page, custom fields | Job > Notes or Materials > one checkbox/edit | Remains editable per job without modifying master |
| Rename a field | Dedicated oversized Edit control | Long-press or compact `⋯` menu | Edit and up/down reachable via tap and screen reader |
| Reorder a job photo | Filename sort | `⋯` > Move up/down; durable order.csv | Persist after process death and ZIP restore |
| Simplify solo workflow | Crew, time and routing mixed into same scroll | Crew, route, time, pricebook switches default off | Hide and re-enable without deleting data |
| Export without private cash ledgers | CSV ZIP six broad switches | PDF or ZIP > tables > exact payment methods and expense categories | Excluded methods absent from exported content |
| Accessible navigation | Labels + min 48dp targets in existing code | Compact visual menu, semantic labels, optional extra move controls | TalkBack / keyboard audit on emulator + device |

## Accounting correctness boundaries

- **Accounts receivable:** a job's invoiced value is not a bank balance and is not proof of an
  issued tax invoice. A/R aging, refunds, unapplied payments and change orders still need
  reliable object models and independent acceptance.
- **Accounts payable:** manual expense rows are not vendor bills or settled liabilities.
  AP subledgers, vendor identity, due dates and approvals are future work.
- **General ledger:** the current app has no controlled chart of accounts, immutable
  journal, debit/credit balancing, audit periods or double-entry posting. Never call
  selective CSV export a GL or a direct QuickBooks integration.
- **Reporting privacy:** do not emit PaymentMethod, RecordedPayments, payment notes,
  balance derivations from excluded ledgers, or expense rows when their categories
  were not selected. Job value reports deliberately omit paid/balance columns so a
  hidden ledger cannot be inferred through totals.
- **QuickBooks:** the ZIP contains manually mapped CSVs and an explicit scope manifest.
  A ZIP is not itself a native QuickBooks import file; verify the product-specific,
  region-specific import mapping before use.
- **PDF:** immediate on-device summary via Android PdfDocument, with scope header,
  pagination and no outbound API. Further polish: printable layout proof with long
  UTF-8 descriptions, RTL scripts, huge datasets, accountant sign-off.
- **Control:** every export is a user-initiated SAF document save, no upload and no
  background data transmission. For backups use separately controlled encrypted export.

## Accessibility as a nonintrusive baseline

Accubook must **not** try to toggle the Android TalkBack service from within the app.
The system accessibility settings and user's preferences control that service.
Semantic labels, keyboard focus and minimum hit targets exist for everyone. The
visual interface defaults to small `⋯` actions, and optional extra move controls are
enabled in Settings > Features. Long-press is never the only way to do an action.
Physical TalkBack, large-text, switch-access and touch-exploration acceptance remains open.

## Launch gates (not yet accepted)

1. Exact HEAD compile, JVM archive/integrity tests, APK signature, emulator smoke.
2. Physical Android 15: job context, 20+ reordered photos, device restart, 1,000+
   contacts, dates/clock, fingerprint/PIN, reminders, Calendar ACTION_INSERT.
3. Export synthetic distinct Cash / Cash App / Bank Transfer and Fuel / Tools / Other
   data. Uncheck Cash App and Other; verify neither appears in PDF or any ZIP CSV,
   including indirectly through derived totals.
4. ZIP round-trip photo order, fields and sample import, then corrupt one photo
   order reference and verify staged restore aborts without changing live data.
5. Manual accessibility check; no release-ready claim from CI alone.
