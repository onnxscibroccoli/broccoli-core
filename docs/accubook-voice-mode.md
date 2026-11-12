# Accubook Voice-to-Text Agentic Mode

**Status:** Design + prototype scaffold (v1). Target: Android 15, 4GB RAM devices. Fully offline common path.

## Overview

Voice-to-text agentic mode enables field contractors to interact with Accubook CRM via speech for common workflows (create job, log material, update status, schedule, record payment) without typing. Design prioritizes reliability on low-end hardware, accessibility (TalkBack compatible), and zero mandatory cloud.

Hybrid architecture: common path is pure keyword + slot-filling with zero ML model. Fallbacks escalate only when needed.

## Architecture Layers

### 1. Keyword + Slot-Filling Layer (Zero-Model Common Path)
- Deterministic intent detection via keyword dictionaries and lightweight regex/pattern matching on STT transcript.
- Slot extraction for entities: customer_name, job_type, date/time, material, amount, status, address.
- Canonical actions mapped to existing Accubook domain operations (customer/job/estimate/invoice/payment/photo/note).
- No model inference on the happy path. Latency target: <100ms post-STT.

### 2. Multiple-Choice Disambiguation with Voice Response
- When intent or slot is ambiguous (e.g., multiple matching customers), present 2-4 options via TTS + UI.
- User responds by voice ("first", "the roofing one", "number two") or tap.
- Confirmed selection fills the slot and proceeds.

### 3. 20-Questions Binary Splits Seeded by STT Transcript
- For high-cardinality slots (e.g., customer from 300+ list) or open-ended clarification.
- Binary questions seeded by partial transcript matches and context ranking (recent jobs, location, schedule).
- Example: "Is this for an existing customer?" → yes/no → further splits by first letter, recent, site address.
- Max depth limited to keep interaction short.

### 4. Context-Ranked Slot Disambiguation
- Rank candidate slots using conversation history, current schedule, last customer, GPS/site context (when permitted), and recent actions.
- Prefer recent/high-frequency entities.

### 5. Tiny 1-3B 4-bit Quantized Classifier Fallback
- Triggered only when keyword match confidence is low or multi-intent detected.
- 1-3B parameter model, 4-bit quantized, run via ONNX Runtime or ExecuTorch.
- Target footprint fits comfortably in 4GB RAM devices alongside the app (model ~0.5-1.5GB quantized).
- Classification only (intent + slot labels); not generative.
- Hot-swap or lazy-load; disabled by default if memory pressure.

### 6. Federated Learning from Contractor Corrections
- On-device logging of user corrections (intent misclassification, slot fills).
- Optional, privacy-preserving federated updates (differential privacy, no raw transcripts leave device).
- Aggregated model improvements shipped as future quantized updates. Opt-in only.

### 7. Hybrid Zero-Model Common Path
- 80%+ of interactions complete without any model.
- Escalation ladder: keyword → context rank → binary questions → multi-choice → tiny classifier.
- Explicit user confirmation before any mutating action (create, update, payment).

## Prototype Flow (Scaffold)

STT input → keyword match → slot extraction → missing-slot detection → single clarifying question → action execution.

See `experiments/accubook/voice_mode/` for the initial prototype.

## Integration Notes

- STT: Android SpeechRecognizer or on-device alternative (no cloud required for common path).
- TTS: Android TextToSpeech for responses.
- Must respect Accubook offline constraints, no INTERNET permission on core path.
- Accessibility: all voice flows have equivalent TalkBack/keyboard paths.
- Ties into existing domain models from draft branches (Nov 5-7 Accubook stack).

## Open Questions / Next

- Exact STT engine selection and accuracy on job-site noise.
- Quantized model training data (synthetic + anonymized corrections).
- Memory profiling on 4GB devices.
- Check `feat/ollama-ci-observatory` branch for reusable on-device inference hooks (currently limited).

Related issues: #83 (release gate), #86 (security/integration).

## Reusable Inference Hooks (checked)

- `feat/ollama-ci-observatory` branch contains a CI workflow for failure analysis using a central Ollama job (Grasshopper). It is diagnostic only and does not provide on-device inference code.
- Existing `docs/ONNX_INTEGRATION.md` and `runtime/onnx_runtime.py` provide a keyword-fallback ONNX intent classifier pattern that can be adapted for the tiny 1-3B fallback path. Prefer ExecuTorch or ONNX Runtime Mobile for Android 15 / 4GB targets.
- No production on-device 4-bit classifier is present yet; the common path remains zero-model.
