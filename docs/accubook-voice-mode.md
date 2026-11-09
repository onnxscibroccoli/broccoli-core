# Accubook Voice-to-Text Agentic Mode

**Status:** Design + prototype scaffold (v1). Target: Android 15, 4 GB RAM devices. Offline-first, no runtime cloud.

## Goals

Provide a voice-driven agentic interface for Accubook field-service CRM so contractors can create/update customers, schedule jobs, log notes, and query status without looking at the screen. Accessibility-first (TalkBack, Switch Access). Must work fully offline.

## Architecture Overview

Hybrid zero-model common path with optional tiny on-device classifier fallback.

```
STT transcript
  → keyword match (exact / fuzzy)
  → slot extraction (regex + lexicon)
  → missing-slot detection
  → single clarifying question (voice + multiple-choice)
  → action execution (WorkspaceStore / domain APIs)
  → confirmation / audit log
```

### 1. Keyword + Slot-Filling Layer

- Intent keywords mapped to Accubook actions (add_customer, schedule_job, add_line, query_balance, etc.).
- Slot extractors for: customer name, date (YYYY-MM-DD or relative), amount, quantity, address fragments, job title.
- Zero-model path handles >80% of common field commands.

### 2. Multiple-Choice Disambiguation with Voice Response

When ambiguity is detected (multiple customers matching name, unclear date):
- Speak options via TTS or system speech.
- Accept spoken selection ("first", "the second one", "Boston job").
- Limit to 3–5 options to stay within cognitive load.

### 3. 20-Questions Binary Splits Seeded by STT Transcript

For open-ended or high-entropy queries:
- Seed a binary decision tree from the transcript tokens.
- Ask yes/no questions that maximally reduce entropy (e.g., "Is this for an existing customer?").
- Cap at 5–7 questions in practice; full 20 only as theoretical bound.

### 4. Context-Ranked Slot Disambiguation

- Maintain short-term conversation context (last customer, last job, current date).
- Rank candidate slot fills by recency, frequency, and geographic proximity (if location available).
- Prefer context over pure lexical match when scores are close.

### 5. Tiny Classifier Fallback (1-3B 4-bit quantized)

- For utterances that fail keyword/slot path.
- ONNX Runtime or ExecuTorch, 4-bit quantization, target <400 MB peak RAM on 4 GB devices.
- Models: distilled intent classifier or small LLM (e.g., quantized Phi-3-mini, Gemma-2B, or custom).
- Loaded only on demand; unloaded after inference.
- Reuses patterns from `runtime/onnx_runtime.py` and `feat/ollama-ci-observatory` hooks where present.

### 6. Federated Learning from Contractor Corrections

- Local correction log (user says "no, I meant the other job").
- Aggregate anonymized correction pairs on-device or via optional opt-in export.
- Periodic local fine-tune of the tiny classifier (or update keyword lexicon).
- No raw transcripts leave the device without explicit consent.

### 7. Hybrid Zero-Model Common Path

- Default path never requires a model.
- Classifier is pure fallback.
- All paths produce the same structured action record for audit and undo.

## Prototype Scaffold

Location: `experiments/accubook/voice/`

- `VoiceAgent.java` (or Kotlin) – Android STT listener + pipeline.
- `KeywordSlotEngine.java` – pure Java keyword/slot layer.
- `ClarificationDialog.java` – single-question UI + voice reply.
- `ActionExecutor.java` – maps filled slots to WorkspaceStore calls.
- Integration point: optional button or always-listening hotword in MainActivity (gated by permission).

## Constraints & Risks

- Android 15 / 4 GB RAM: avoid loading large models concurrently with camera or large CSVs.
- STT accuracy in noisy job sites; require confirmation for financial actions.
- Privacy: transcripts stay local; no INTERNET permission by default.
- Accessibility: every clarifying question must be TalkBack-friendly.
- Existing Accubook draft branches (Nov 5–7) are experimental; voice layer must not assume production data schema stability.

## Next Steps

1. Wire STT (Android SpeechRecognizer or on-device Whisper-tiny/Parakeet via ONNX).
2. Implement keyword lexicon for core CRM actions.
3. Add unit tests for slot extraction and missing-slot detection.
4. Prototype single clarifying question flow.
5. Measure RAM/CPU on target devices.
6. Document errors found during draft-branch testing (see `docs/accubook-draft-errors.md`).

Related: Accubook release gate issues, `runtime/onnx_runtime.py`, feat/ollama-ci-observatory.
