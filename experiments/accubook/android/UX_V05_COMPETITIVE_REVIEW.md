# Accubook v0.5 — evidence-based mobile UX review

**Date:** 2026-11-07  
**Maturity:** Engineering implementation / review; **not** production acceptance.  
**Sources:** Actual Accubook Android code and publicly accessible vendor UI screenshots/help. No internal competitor accounts or paid product testing. Visual parity across identical devices has **not** been verified.

## Decision criteria

1. Reduce taps and scrolling for the user currently working at a job.
2. Adopt a competitor pattern only when it improves a measurable field task.
3. Preserve offline use, local ownership, editable templates, and no runtime AI.
4. Keep screen-reader/keyboard access available without duplicating every action
   as an enormous permanent button.
5. Never hide user records when a feature is disabled: hide the module, not its data.

## Direct visual / interaction comparisons

| Pattern | Evidence from competing UI | Accubook response | What was NOT copied |
| --- | --- | --- | --- |
| Focused job details | Jobber's Visit / Details / Notes top rail separates workflows (Jobber Help Center, updated Oct 2026). | Horizontal job focus rail: Overview, Photos, Notes, Materials, Money, Checklist, Schedule, and opt-in Time/Route. | Mandatory hosted sync, fixed vendor workflow or sales-admin restrictions. |
| Quick photo access | AccuLynx Field App advertises a standalone job album with thumbnail grid (vendor UI, 2023). | Separate photo-only job section; existing bulk import and preview preserved. | Proprietary photo/supplement pipelines. **Atomic photo order and move up/down are now implemented; the compact grid and drag gesture remain pending.** |
| Field documents | Jobber surfaces visit forms/checklists alongside detail and notes. | Per-job editable fields; long-press plus visible compact overflow with edit, up/down, required and removal; existing job values preserved. | Large edit/remove button blocks that dominate the job page. |
| Optional crew/timers | Housecall Pro showcases job status, checklists, time tracking and team workflows. | Crew and worker time are independent local switches, default off for solo use; original records persist if disabled. | Forced team setup or paid feature gating. |
| Calendar handoff | Competitors consolidate appointment and work status in job context. | Dedicated Schedule tab; explicit Android calendar-editor handoff. | Unreliable automatic Google Calendar synchronization. |
| Accounting exports | Existing Accubook ZIP grouped broad report sections and included payment totals in job values even when payments were deselected. | Two separate actions: native quick PDF aggregate or per-section CSV ZIP, both with opt-in payment-method and expense-category filters. Jobs CSV never includes payment/balance columns. | Implying a generic CSV is guaranteed QuickBooks-ready or a reconciled general ledger. |

Vendor primary references:
- Jobber Jobs in the Jobber App: https://help.getjobber.com/en/articles/jobs-in-the-jobber-app/
- Jobber Notes and Attachments: https://help.getjobber.com/en/articles/notes-and-attachments-in-the-jobber-app/
- AccuLynx Field App image and details: https://acculynx.com/new-acculynx-field-app/
- Housecall Pro Mobile FAQ: https://help.housecallpro.com/en/articles/4747652-housecall-pro-mobile-faq
- Housecall Pro Mobile photos: https://help.housecallpro.com/en/articles/10159740-capture-and-upload-photos-videos-on-mobile

## Acceptance matrix — do not confuse implementation with proof

| Requirement | Current state | Verification still required |
| --- | --- | --- |
| Stable-ID master/per-job field reordering | Implemented; atomic CSV rewrite | Real device reorder, repeated relaunch, backup/restore |
| Small overflow + long-press reorder | Implemented; move up/down accessible without gesture | Android 15/physical accessibility and hit target review |
| Focused job sections | Implemented, preserves current actions | Emulator + physical navigation/regression |
| Solo feature switches | Implemented for real modules; CSV data untouched | Persistence, default checks, retoggle and disabled-data test |
| Quick PDF summary | Implemented with Android PdfDocument | Emulator PDF bytes, real print readability, 1+ page |
| Selective accounting CSV ZIP | Implemented, explicit method/category allow-lists | ZIP content filter on real data, import mapping |
| Contacts separate from customers | Preexisting PR #87 | Physical contact permission/import |
| Bulk photos, local dumpster reminder, biometric/PIN | Existing owner-tested | No-regression on new APK |
| Photo order through accessible action menus | Implemented: atomic photo_order.csv and ZIP restore validation | Emulator and real-device reorder/restore; grid drag remains pending |
| Checklist drag gesture | Not implemented; field-level up/down works | Drag interaction and TalkBack non-gesture alternative |
| Customer/job color across all views | Partially present | Color audit of all list/calendar surfaces |
| Built-in brand/app logo resources | Pending asset packaging | Launcher/splash/invoice rendering |
| Recurring jobs, multi-property and route density | **Planned only** | Do not claim finished |
| Runtime provider sync / true QuickBooks import | **Not implemented** | No false automation claims |

## Accounting boundaries

A quick PDF intentionally contains aggregates, not customer-level or bank-level
transaction lines. A selected CSV ZIP can contain personally identifiable
information. CSV data may require field mapping by QuickBooks and should be
reviewed before import. Both outputs are created through Android's
ACTION_CREATE_DOCUMENT provider; the app does not send the records online.

**Privacy invariant:** When payments are not selected, neither the payments CSV
nor receipt/balance columns may appear through the jobs CSV. Only chosen methods
and expense categories are exported; there is no hidden default inclusion of
Cash App or cash entries.

## Accessibility policy

Accubook is visually driven and touch-first, not a screen-reader-only interface.
It still provides named controls, a visible overflow alternative to long-press,
status text alongside color, and user-controlled on/off modules. Android controls
TalkBack itself. A system Accessibility Settings handoff is provided; the app
does not use elevated permissions to toggle an Android accessibility service.
Comprehensive TalkBack, font scaling, switch access and WCAG-oriented testing
remain a **production release gate**, even though normal users need not turn
on extra accessibility UI.

## Next verified increments

1. Resolve Android emulator smoke and run fresh physical-device navigation.
2. Verify newly implemented photo ordering metadata and the backup/restore schema on device.
3. Introduce role-friendly photo grids and field-level reorder drag gesture
   without removing overflow actions.
4. Implement context-aware color in every job/customer/calendar surface.
5. Integrate owner-supplied artwork as Android launcher/business branding assets
   and verify print/PDF logos.
6. Add optional report date ranges, saved export presets and general-ledger
   account/category mapping, once accounting records are modeled correctly.
7. Release only after financial data integrity, backup restore and accessibility
   acceptance; APK compile alone is not launch proof.
