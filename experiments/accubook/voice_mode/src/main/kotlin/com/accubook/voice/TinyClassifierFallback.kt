package com.accubook.voice

/**
 * Stub for tiny 1-3B 4-bit quantized classifier fallback.
 * Runs via ONNX Runtime or ExecuTorch. Lazy-loaded, memory-aware.
 * Only used when keyword confidence is low. Not on the common path.
 *
 * Target: fits in 4GB RAM devices (~0.5-1.5GB quantized model).
 * Classification only (intent + slot labels). No generation.
 */
class TinyClassifierFallback {
    fun classify(transcript: String): IntentMatch? {
        // TODO: Load ONNX/ExecuTorch session on first use, with memory check.
        // Return null if memory pressure or model unavailable.
        return null
    }

    fun isAvailable(): Boolean = false  // Default off
}
