# Accubook v0.5 — actual emulator visual audit against field CRM references

**Audit date:** 2026-11-07 (America/New_York)
**Captured build:** commit `393739bfef3daf1b569ff2d6042b61c74c0119f8`
**Test:** GitHub Actions emulator job `42395417813` — **passed**.
**Artifact:** `accubook-ui-evidence` (five PNG screenshots and matching
accessibility XML) from the `Accubook Android Emulator UI Smoke` workflow.
**Device profile:** 1080×1920, font scale 1.2; all records are a fictional
in-app sample job. Images are screenshots from the compiled Android application,
**not** the aspirational design mockups generated earlier.

## Concrete findings from five screens

| Captured screen | Observed actual behavior | Friction / design tradeoff | Decision |
| --- | --- | --- | --- |
| 01-home.png | Distinct top heading, 2×3 six-workspace buttons, today's counts and dollar totals in dark navy, and primary quick actions below first screen. | Typography and contrast clear, but zero-value summary occupies significant vertical area and pushes actions down. | Keep actual dashboard metrics; add direct **Quick PDF / selective accounting report** action. Future: optional collapse of zero-state statistics and customizable action order. |
| 02-job-overview.png | Full title/customer/date, 2×3 global buttons, 2×3 job section buttons, oversized customer button, then Call/Directions and status details. | Repeated global navigation uses two rows and customer link dominates another row before field actions. | **Changed after audit:** replace global job navigation with one 3-button context bar (Jobs / Home / More). Keep customer button only in Overview. |
| 03-job-notes.png | Clearly distinguished Notes active state, notes are readable, editor button and checklist heading are discoverable without opening a second screen. | Repeated six global navigation buttons and customer bar unnecessarily compete with note editing. | **Changed:** compact contextual navigation and no customer CTA on Notes. The `⋯` menu remains a non-gesture editing alternative for field controls. |
| 04-job-billing.png | Invoice/estimate preview actions are visible, but monetary detail and line items appear further down the scroll. | Redundant global navigation and unrelated customer button displace billing information. | **Changed:** compact contextual navigation, remove duplicate customer CTA. Preserve separate Billing mode rather than an all-purpose long job page. |
| 05-job-photos.png | Distinct Photos section; `Add photo from device` and `Import multiple photos` are direct actions; empty-state message is clear. | Two rows of global workspace buttons and duplicate customer button push the photo gallery and metadata off-screen. | **Changed:** job-only compact nav and no repeated customer CTA. Keep existing local bulk picker; avoid cloud uploading. |

## Source-grounded competitor comparisons

- **Jobber** ([official jobs article](https://help.getjobber.com/en/articles/jobs-in-the-jobber-app/)):
  three visit-centric tabs (Visit, Details, Notes) and checklist completion warning.
  **Accubook:** focused job sections and required-field gate. Jobber's fewer top
  tabs reinforce reducing navigation chrome, but billing/materials/photos remain
  separate Accubook contexts because they carry distinct field tasks.
- **ServiceTitan** ([Field Mobile guide](https://help.servicetitan.com/how-to/overview-of-the-servicetitan-field-mobile-app-job-details-screen)):
  job card exposes schedule, Call and Directions. **Accubook:** uses local native
  dialer and map intents, not AI assistance or mandatory cloud sync.
- **Housecall Pro** ([mobile attachments](https://help.housecallpro.com/en/articles/10159740-capture-and-upload-photos-videos-on-mobile)):
  distinct camera and library actions, failed-upload handling. **Accubook:** preserve
  one-tap bulk on-device import and local storage; no hidden upload queue.
- **QuickBooks Online** ([CSV import documentation](https://quickbooks.intuit.com/learn-support/en-us/help-article/import-export-data-files/common-questions-importing-data-quickbooks-online/L4OYJRFdj_US_en_US)):
  import formats and supported transaction types depend on the destination module.
  **Accubook:** PDF for immediate readable reports, ZIP of explicit CSV tables for
  a controlled manual mapping; not a native QuickBooks package.

## Visual principles tested and retained

- Large readable typography on a dark background, distinct blue primary actions,
  good contrast and a clear selected-job section marker.
- All primary buttons remain visible/tappable under a 1.2 font scale.
- No essential action uses a long-press gesture alone: labeled overflow button
  and accessible menu remain available.
- TalkBack is an **OS service**, not a mandatory Accubook visual interface mode.
  Android's own controls manage screen-reader activation. A11y acceptance must
  still prove keyboard, focus order, large text and TalkBack on a real device.
- App icon is the owner-provided dog/hardhat; business documents use the
  distinct Jules Gutter Cleaning leaf PNG (user-initiated choice).

## Unverified after these screenshot observations

Changes to job-level compact nav and removal of redundant customer action were
committed **after** the screenshot set. Do not pass their visual gate on the
strength of the old screen captures: rerun the exact-head emulator screenshot
workflow and inspect the updated pictures. A successful build is not proof
that a compact navigation change improved user experience.

External/production acceptance still requires physical Android 15 touch and
TalkBack checks, real-size photo and PDF export layout, screened accounting
ledger exclusion, backups after relaunch, and measured operator task time.
There is no evidence here that a user completed an end-to-end QuickBooks import.
