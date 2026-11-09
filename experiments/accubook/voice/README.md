# Accubook Voice Prototype

Scaffold for the voice-to-text agentic pipeline described in `docs/accubook-voice-mode.md`.

## Files

- `VoiceAgent.java` – pure-Java keyword/slot/clarification pipeline. No Android dependencies so it can be unit-tested on the host.

## Integration notes (Android 15 / 4 GB)

1. Add SpeechRecognizer or on-device STT (e.g., ONNX Parakeet-tiny).
2. Call `VoiceAgent.process(transcript)`.
3. If `clarification != null`, speak the question and listen for the answer, then re-process with context.
4. If `ready`, call domain action on `WorkspaceStore`.
5. Optional tiny 4-bit classifier only when keyword match fails.

See design doc for full architecture (binary splits, context ranking, federated corrections, etc.).
