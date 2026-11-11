package com.accubook.voice

/**
 * Lightweight slot extraction stubs. Extend with regex, dictionaries, and context ranking.
 */
class SlotExtractor {
    fun extract(transcript: String, intent: String): Map<String, String> {
        val slots = mutableMapOf<String, String>()
        val lower = transcript.lowercase()

        // Stub examples — replace with real parsers
        if (lower.contains("roofing") || lower.contains("roof")) slots["job_type"] = "roofing"
        if (lower.contains("exterior")) slots["job_type"] = "exterior"

        // Amount stub
        val amountMatch = Regex("\\$([0-9,.]+)").find(lower)
        if (amountMatch != null) slots["amount"] = amountMatch.groupValues[1]

        // Date stub (very basic)
        if (lower.contains("tomorrow")) slots["datetime"] = "tomorrow"
        if (lower.contains("today")) slots["datetime"] = "today"

        return slots
    }
}
