package com.accubook.voice

/**
 * Prototype entry point for Accubook voice-to-text agentic mode.
 * Target: Android 15, 4GB RAM. Offline common path (zero-model).
 *
 * Flow: STT → keyword match → slot extraction → missing-slot detection
 *       → single clarifying question (or binary/multi-choice) → action execution.
 *
 * Escalation ladder (stubbed): keyword → context rank → binary splits
 * → multi-choice → tiny 4-bit classifier (ONNX Runtime / ExecuTorch).
 */
class VoiceAgent {
    private val matcher = KeywordMatcher()
    private val extractor = SlotExtractor()
    private val questionGen = ClarifyingQuestion()
    private val executor = ActionExecutor()
    // Optional fallback; disabled by default for 4GB devices
    private val classifier: TinyClassifierFallback? = null

    fun processTranscript(transcript: String): VoiceResult {
        val match = matcher.match(transcript)
        if (match == null) {
            // Could escalate to classifier here if enabled
            return VoiceResult(
                status = "clarification",
                message = questionGen.fallbackQuestion()
            )
        }

        val slots = extractor.extract(transcript, match.intent)
        val missing = match.requiredSlots.filter { !slots.containsKey(it) }

        if (missing.isNotEmpty()) {
            val q = questionGen.forSlot(missing.first(), match.intent)
            return VoiceResult(
                status = "clarification",
                message = q
            )
        }

        // Production: require explicit confirmation before mutation
        return executor.execute(match.intent, slots)
    }
}

data class VoiceResult(
    val status: String,  // "success", "clarification", "error"
    val message: String,
    val action: String? = null
)
