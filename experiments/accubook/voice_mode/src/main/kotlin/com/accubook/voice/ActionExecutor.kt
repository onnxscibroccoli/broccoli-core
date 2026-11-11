package com.accubook.voice

/**
 * Stub action executor. Wire to Accubook domain layer (customers, jobs, invoices, etc.).
 * Always require explicit confirmation for mutations in production.
 */
class ActionExecutor {
    fun execute(intent: String, slots: Map<String, String>): VoiceResult {
        // Stub — log and return success message
        val summary = "Executing $intent with slots: $slots"
        return VoiceResult(
            status = "success",
            message = "Done. $summary",
            action = intent
        )
    }
}
