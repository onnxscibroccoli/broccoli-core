package com.accubook.voice

/**
 * Prototype entry point for Accubook voice-to-text agentic mode.
 * Target: Android 15, 4GB RAM. Offline common path.
 *
 * Flow: STT → keyword match → slot extraction → missing-slot → clarifying question → action.
 */
class VoiceAgent {
    private val matcher = KeywordMatcher()
    private val extractor = SlotExtractor()
    private val questionGen = ClarifyingQuestion()
    private val executor = ActionExecutor()

    fun processTranscript(transcript: String): VoiceResult {
        val match = matcher.match(transcript)
        if (match == null) {
            return VoiceResult.ClarificationNeeded(questionGen.fallbackQuestion())
        }

        val slots = extractor.extract(transcript, match.intent)
        val missing = match.requiredSlots.filter { !slots.containsKey(it) }

        if (missing.isNotEmpty()) {
            val q = questionGen.forSlot(missing.first(), match.intent)
            return VoiceResult.ClarificationNeeded(q)
        }

        return executor.execute(match.intent, slots)
    }
}

data class VoiceResult(val status: String, val message: String, val action: String? = null)
