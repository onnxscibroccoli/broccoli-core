package com.accubook.voice;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Prototype scaffold for Accubook voice-to-text agentic mode.
 * Target: Android 15, 4 GB RAM. Hybrid zero-model common path.
 *
 * Pipeline: STT text -> keyword match -> slot extraction -> missing-slot detection
 *           -> single clarifying question -> action execution.
 *
 * This is a pure-Java skeleton. Wire to Android SpeechRecognizer and WorkspaceStore
 * in the Android module. No model loaded by default.
 */
public final class VoiceAgent {

    public static class ActionResult {
        public final String intent;
        public final Map<String, String> slots;
        public final String clarification; // null if ready to execute
        public final boolean ready;

        public ActionResult(String intent, Map<String, String> slots, String clarification) {
            this.intent = intent;
            this.slots = Collections.unmodifiableMap(new HashMap<>(slots));
            this.clarification = clarification;
            this.ready = clarification == null;
        }
    }

    private static final Map<String, String> KEYWORDS = new HashMap<>();
    static {
        KEYWORDS.put("add customer", "add_customer");
        KEYWORDS.put("new customer", "add_customer");
        KEYWORDS.put("schedule job", "schedule_job");
        KEYWORDS.put("new job", "schedule_job");
        KEYWORDS.put("add line", "add_line");
        KEYWORDS.put("add item", "add_line");
        KEYWORDS.put("what's my balance", "query_balance");
        KEYWORDS.put("show jobs", "list_jobs");
    }

    private static final Set<String> REQUIRED_SLOTS = new HashSet<>(Arrays.asList(
        "customer_name", "job_title", "date", "description", "quantity", "rate"
    ));

    public ActionResult process(String transcript) {
        if (transcript == null || transcript.trim().isEmpty()) {
            return new ActionResult("unknown", Collections.emptyMap(),
                "I didn't hear anything. Please try again.");
        }
        String low = transcript.toLowerCase(Locale.US).trim();

        // 1. Keyword match
        String intent = matchKeyword(low);
        if (intent == null) {
            return new ActionResult("unknown", Collections.emptyMap(),
                "I didn't recognize that command. Try 'add customer' or 'schedule job'.");
        }

        // 2. Slot extraction
        Map<String, String> slots = extractSlots(low, intent);

        // 3. Missing-slot detection
        String missing = findMissingSlot(intent, slots);
        if (missing != null) {
            return new ActionResult(intent, slots, askFor(missing));
        }

        // Ready for execution
        return new ActionResult(intent, slots, null);
    }

    private String matchKeyword(String low) {
        for (Map.Entry<String, String> e : KEYWORDS.entrySet()) {
            if (low.contains(e.getKey())) return e.getValue();
        }
        return null;
    }

    private Map<String, String> extractSlots(String low, String intent) {
        Map<String, String> slots = new HashMap<>();
        // Simple date
        Matcher date = Pattern.compile("(\d{4}-\d{2}-\d{2})").matcher(low);
        if (date.find()) slots.put("date", date.group(1));
        // Quantity
        Matcher qty = Pattern.compile("(\d+(?:\.\d+)?)\s*(?:units?|items?|each)").matcher(low);
        if (qty.find()) slots.put("quantity", qty.group(1));
        // Amount / rate
        Matcher rate = Pattern.compile("\$?(\d+(?:\.\d{2})?)").matcher(low);
        if (rate.find()) slots.put("rate", rate.group(1));
        // Naive name / title capture (improve with lexicon later)
        if (intent.equals("add_customer") || intent.equals("schedule_job")) {
            // Placeholder: real implementation would use NER or context
            slots.put("customer_name", "(extracted)");
        }
        if (intent.equals("schedule_job") || intent.equals("add_line")) {
            slots.put("job_title", "(extracted)");
            slots.put("description", "(extracted)");
        }
        return slots;
    }

    private String findMissingSlot(String intent, Map<String, String> slots) {
        switch (intent) {
            case "add_customer":
                if (!slots.containsKey("customer_name")) return "customer_name";
                break;
            case "schedule_job":
                if (!slots.containsKey("customer_name")) return "customer_name";
                if (!slots.containsKey("job_title")) return "job_title";
                if (!slots.containsKey("date")) return "date";
                break;
            case "add_line":
                if (!slots.containsKey("description")) return "description";
                if (!slots.containsKey("quantity")) return "quantity";
                if (!slots.containsKey("rate")) return "rate";
                break;
            default:
                break;
        }
        return null;
    }

    private String askFor(String slot) {
        switch (slot) {
            case "customer_name": return "Which customer?";
            case "job_title": return "What is the job title?";
            case "date": return "What date? Say YYYY-MM-DD or today.";
            case "description": return "What is the line description?";
            case "quantity": return "How many?";
            case "rate": return "What is the unit rate?";
            default: return "Please provide more details.";
        }
    }

    /** Execute when ready. Caller supplies WorkspaceStore or domain service. */
    public String execute(ActionResult result) {
        if (!result.ready) throw new IllegalStateException("Not ready: " + result.clarification);
        // TODO: call Accubook WorkspaceStore methods
        return "Executed " + result.intent + " with slots " + result.slots;
    }
}
