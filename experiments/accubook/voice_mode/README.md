# Accubook Voice Mode Prototype

Scaffold for the hybrid voice-to-text agentic framework.

See `../../docs/accubook-voice-mode.md` for the full design.

## Run

```bash
python experiments/accubook/voice_mode/prototype.py
```

## Integration notes

- STT assumed provided by Android SpeechRecognizer or on-device Whisper-class model.
- Action execution to be wired to Accubook domain (CSV/JSON workspace).
- ONNX classifier fallback can reuse `runtime/onnx_runtime.py` pattern from `feat/ollama-ci-observatory-20261013`.
- Feature-flag the entire mode until core CRM acceptance gates (#83) pass.
