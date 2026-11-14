# Accubook Voice-to-Text Agentic Mode

**Status:** Design + prototype scaffold (v1). Optional offline layer for Accubook field-service CRM.
**Target:** Android 15, devices with ≤4 GB RAM. Fully offline core path. No runtime cloud dependency for common actions.
**Related:** Accubook PRODUCT_REQUIREMENTS.md, issues #83 (release gate), #86 (encryption/acceptance).

## Goals

Enable contractors to drive Accubook via voice (STT transcript) for high-frequency field actions (log note, schedule job, record payment, request material, attach photo note) without leaving the job site. Accessibility-first: works with TalkBack, large text, and low-vision.

## Architecture Layers (Hybrid)

### 1. Keyword + Slot-Filling Layer (Zero-Model Common Path)
- Fast, deterministic, pure Python / Kotlin.
- Keyword intent detection (e.g., "schedule", "note", "payment", "material", "photo").
- Slot extraction via simple patterns / regex / gazetteers for: customer name, job ID/date, amount, material, note text, site.
- Missing-slot detection triggers a single clarifying question.
- Reuses pattern from `runtime/onnx_runtime.py` keyword fallback.

### 2. Multiple-Choice Disambiguation with Voice Response
- When slots are ambiguous (e.g., two customers named "Smith"), present 2–4 spoken options.
- User replies with number, ordinal, or short phrase.
- Confirmation step before destructive or financial actions.

### 3. 20-Questions Binary Splits (Seeded by STT Transcript)
- For low-confidence or novel intents, fall back to binary yes/no questions that maximally reduce entropy.
- Seeded with entities already extracted from the STT transcript to minimize questions.
- Cap at 5–7 questions in practice; full 20 only as theoretical bound.

### 4. Context-Ranked Slot Disambiguation
- Rank candidate slots using recent job context, open schedule, current customer, and device location (optional, privacy-gated).
- Prefer most recent or currently open job.

### 5. Tiny 1–3B 4-bit Quantized Classifier Fallback
- ONNX Runtime or ExecuTorch.
- 4-bit quantized model ≤200–400 MB resident for 4 GB RAM devices.
- Only invoked when keyword confidence < threshold or novel phrasing.
- Intent classification + slot tagging; never full generative LLM.
- Model optional; pure keyword path always available.

### 6. Federated Learning from Contractor Corrections
- On-device logging of (transcript, corrected slots/intent, confirmation).
- Differential privacy / secure aggregation hooks for future optional federated updates.
- Local fine-tune of the tiny classifier only; no raw audio leaves device.
- Explicit opt-in.

### 7. Hybrid Zero-Model Common Path
- 80 %+ of field actions resolve with keyword + slots + one clarifying question.
- Model path is progressive enhancement only.

## Prototype Flow (v1 Scaffold)

```
STT transcript
  → keyword match
  → slot extraction
  → missing-slot detection
  → single clarifying question (voice + UI)
  → user response
  → action execution (or confirmation)
  → audit log
```

Target integration points: Accubook domain actions (create note, schedule, record payment stub, etc.) via existing CSV/JSON workspace.

## Constraints & Trade-offs

- **RAM:** 4 GB limit → no large models; 4-bit + keyword priority.
- **Privacy:** No audio upload; optional model download only; federated is opt-in and aggregated.
- **Accessibility:** All questions have UI equivalents; voice responses are optional.
- **Offline:** Core path has zero network.
- **Correctness:** Financial and destructive actions always require explicit confirmation.

## Next Steps

- Wire to real Accubook domain actions on an Accubook feature branch.
- Add unit tests for slot extraction and missing-slot logic.
- Device validation on Android 15 / 4 GB.
- Quantized model training pipeline (separate).
- Integration with TalkBack and Switch Access.
