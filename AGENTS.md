# Broccoli Core — provider-agnostic agent operating contract

This repository hosts Android/Termux automation and experimental model orchestration. **This file is not evidence that a feature has been implemented.** Read the most relevant issue, current branch, local tests and acceptance evidence before claiming a capability.

## Repository boundaries

- **Broccoli Core**: on-device event bus, accessibility/authorized Rish-Shizuku UI automation, provider orchestration, Gemini research triggers, model-quality gates, support escalation.
- **`roofmeasure/` on `feat/roofmeasure-dev`**: RoofMeasure measurement engine and three planned APK product variants. Read `roofmeasure/HANDOFF.md` and `roofmeasure/CODEVELOP.md` on that branch before modifying it. Do not bump past 0.1.7.x, merge, or publish stable releases without required user acceptance.
- **Grasshopper**: OmniKali execution control plane, workload scheduling, Git-backed job state, Kali worker resilience.
- **Helix**: AWS/OCI infrastructure, identity, remote GUI/gateway and cloud deployment substrate. Do not make cloud Kali restoration a Broccoli Core implementation task.
- **Accubook / Lattice / TCL-orc**: independent project-specific requirements and issue trackers.

## Priority issue map (2026-11-18)

- Deep Research via authorized Android virtual display: #113 (depends on #66).
- Multi-model Governor and verified Git-first agent handoffs: #114 (relates to #12).
- Provider support escalation and usage-credit request workflow: #115.
- Roof multi-epoch LiDAR, skylight/chimney classification and physical uncertainty: #116.
- Three separately installable RoofMeasure/PropertyMeasure APKs: #117.
- Cloud execution: [Grasshopper #214](https://github.com/onnxscibroccoli/Grasshopper/issues/214) and [Helix #68](https://github.com/onnxscibroccoli/helix/issues/68), not this repo.

## Governor event and artifact discipline

Model output is a **candidate**, never a verified delivery. Every run has:

1. `task_id`, `correlation_id`, user requirement and explicit acceptance contract.
2. Authorized provider/session identity and usage/attempt budgets; subscription access does not automatically confer API entitlement.
3. Immutable `source_repo`, `branch`, `base_sha`, module owner and protected paths.
4. Events: `task.assigned` → `attempt.started` → `artifact.submitted` → `verification.passed|failed` → `handoff.persisted` or `task.blocked`; replay must be idempotent.
5. Evidence: file list, build/tests performed, PASS/FAIL/NOT_PROVEN, source SHA, verified artifact URL+SHA-256, known limitations, exact next step.
6. Governor-enforced bounded retries and model handoffs. Failed attempts must preserve causes, not silently retry or reword the same prompt.

For an agent handoff, publish a durable GitHub branch/PR/issue comment **before** ending a session. A link to a bot's ephemeral workspace is not a handoff. Preserve incomplete work in a review branch or label it unrecoverable, with exact missing data. Exclude credentials and sensitive user data from repositories or diagnostics.

## Authorization and safety

- Non-root Android documented interfaces first; Shizuku/Rish only within granted permissions. A UI display needs live acceptance, not merely package detection.
- Human interaction wins over automated input. Stop for CAPTCHA, authentication prompts, missing permissions, ambiguous deletion or external support submission without an approved consent policy.
- Avoid unsupported scraping bypasses, quota/entitlement circumvention, production modification and uploading private chat/screenshots.
- A failure incident may draft and request a provider support review or usage credit, **never assert credits have been awarded** without provider evidence.
- Validate LiDAR measurements and physical material assumptions. No fabricated precision, dates, models or tax/permit records.

## Work loop

1. Read this file and targeted issue, then the closest code/test/branch handoff. Avoid recursively loading historical mirrors or provider session secrets.
2. Implement **one narrow reversible change**.
3. Run targeted tests and then appropriate broader CI. Root Python suite:
   `python3 -m unittest discover -s tests -t . -v`.
4. If building RoofMeasure, use its branch-local instructions and APK workflow; preserve three-artifact product topology but do not pretend all variants already exist.
5. Record test command/exit status, artifact SHA, and missing live/physical-device proof.
6. Update README/docs/issue evidence and open a **draft PR** for human review. Never auto-merge solely on agent-generated tests.

A passing unit test does not establish Android device behavior, provider UI success, cloud entitlement, roof pitch truth or production readiness.
