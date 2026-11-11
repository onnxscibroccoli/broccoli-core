package com.accubook.voice

/**
 * Generates a single clarifying question for missing slots.
 * Supports multi-choice and binary-split patterns in later iterations.
 */
class ClarifyingQuestion {
    fun forSlot(slot: String, intent: String): String {
        return when (slot) {
            "customer" -> "Which customer is this for?"
            "job_type" -> "What type of job — roofing, exterior, or other?"
            "material" -> "Which material should I log?"
            "job" -> "Which job does this apply to?"
            "status" -> "What status should I set — scheduled, in progress, or complete?"
            "datetime" -> "What date and time?"
            "amount" -> "What is the payment amount?"
            else -> "Please provide the $slot."
        }
    }

    fun fallbackQuestion(): String = "I didn't catch that. Try saying create job, log material, or update status."
}
