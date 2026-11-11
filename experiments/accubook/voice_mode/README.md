# Accubook Voice Mode Prototype Scaffold

Target: Android 15, 4GB RAM. Offline common path.

## Flow

```
STT transcript
  → KeywordMatcher.match(transcript) → Intent + partial slots
  → SlotExtractor.extract(transcript, intent)
  → MissingSlotDetector.detect(intent, slots)
  → if missing: ClarifyingQuestion.generate_one() → TTS / UI
  → else: ActionExecutor.execute(intent, slots)
```

## Files

- `VoiceAgent.kt` — Android entry point (SpeechRecognizer + TTS hooks).
- `KeywordMatcher.kt` — Deterministic keyword/intent matching.
- `SlotExtractor.kt` — Entity extraction stubs.
- `ClarifyingQuestion.kt` — Single-question generator.
- `ActionExecutor.kt` — Stub to domain layer (customer/job/etc.).

## Next Steps

1. Wire to real Accubook domain models from integrated-crm branch.
2. Add unit tests for keyword coverage.
3. Profile memory with optional quantized classifier.
4. Integrate binary-split and multi-choice UI/TTS.
