# ONNX Runtime Integration

This is the **real** ONNX integration for Broccoli Core — distinct from the
`OnyxRuntime` provider router (which is just an event-driven dispatcher).

## What it does

`runtime/onnx_runtime.py` loads a local ONNX model (via `onnxruntime`) for
intent classification. If no model file is present, or `onnxruntime` isn't
installed, it falls back to a pure-Python keyword matcher. The fallback
means the stack works on a stock Termux Python with zero extra packages.

## Usage

```python
from runtime.onnx_runtime import default_classifier
clf = default_classifier()  # or pass a model path
print(clf.classify("turn on bluetooth"))
# -> {'intent': 'toggle_bluetooth', 'score': 1.0, 'source': 'keyword'}
```

Set `BROCCOLI_ONNX_MODEL=/path/to/model.onnx` to load a real model.

## Why this matters

The master vision (issue #28) inverts the data-harvesting model: sensors
and inference run *for* the user, not for advertisers. ONNX on-device is
the mechanism — no cloud round-trip, no telemetry leak, full user control.

## Tests

`tests/test_onnx_runtime.py` — fully offline, no model file required.
