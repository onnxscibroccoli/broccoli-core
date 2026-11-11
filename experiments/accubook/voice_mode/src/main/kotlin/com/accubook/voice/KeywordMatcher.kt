package com.accubook.voice

/**
 * Deterministic keyword + pattern matching for intents.
 * Zero-model common path.
 */
data class IntentMatch(val intent: String, val requiredSlots: List<String>, val confidence: Float = 1.0f)

class KeywordMatcher {
    private val intents = mapOf(
        "create_job" to listOf("create job", "new job", "start job", "add job"),
        "log_material" to listOf("log material", "add material", "material request", "order material"),
        "update_status" to listOf("update status", "mark complete", "job status", "complete job"),
        "schedule" to listOf("schedule", "set appointment", "book time"),
        "record_payment" to listOf("record payment", "log payment", "payment received", "paid")
    )

    private val required = mapOf(
        "create_job" to listOf("customer", "job_type"),
        "log_material" to listOf("material", "job"),
        "update_status" to listOf("job", "status"),
        "schedule" to listOf("customer", "datetime"),
        "record_payment" to listOf("job", "amount")
    )

    fun match(transcript: String): IntentMatch? {
        val lower = transcript.lowercase()
        for ((intent, keywords) in intents) {
            if (keywords.any { lower.contains(it) }) {
                return IntentMatch(intent, required[intent] ?: emptyList())
            }
        }
        return null
    }
}
