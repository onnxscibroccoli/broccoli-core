package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/** Runs with bare javac/java in CI, without Android, servers or internet. */
public final class AnnotationRecordsSmoke {
    private AnnotationRecordsSmoke() {}
    private static void check(boolean ok, String what) {
        if (!ok) throw new AssertionError(what);
    }

    public static void main(String[] args) throws Exception {
        List<AnnotationRecords.Entry> notes = new ArrayList<>();
        notes = AnnotationRecords.upsert(notes, "a", "main/jobs", "job:42/photo:a",
            "/layout/photo[1]", "ImageView", "Photo 2", "Dragging is confusing",
            "2026-11-07T20:00:00Z");
        check(notes.size() == 1, "create");
        String firstTime = notes.get(0).created;
        notes = AnnotationRecords.upsert(notes, "b", "main/jobs", "job:42/photo:a",
            "/layout/photo[4]", "ImageView", "Photo 5",
            "Jiggle then drop:\nExpected \"move\" & keep", "2026-11-07T20:10:00Z");
        check(notes.size() == 1 && notes.get(0).id.equals("a"), "upsert does not duplicate");
        check(notes.get(0).created.equals(firstTime), "original time retained");
        check(notes.get(0).updated.equals("2026-11-07T20:10:00Z"), "updated time");
        check(notes.get(0).path.equals("/layout/photo[4]"), "current hierarchy path stored");
        notes = AnnotationRecords.upsert(notes, "c", "main/business", "dashboard:export",
            "/screen[0]/button[1]", "Button", "Export", "Use \\ backslash,\t tab",
            "2026-11-07T20:11:00Z");
        String csv = AnnotationRecords.write(notes);
        List<AnnotationRecords.Entry> reload = AnnotationRecords.read(csv);
        check(reload.size() == 2 && reload.get(0).note.equals(notes.get(0).note),
            "CSV quoting/UTF-8 round-trip");
        check(AnnotationRecords.find(reload, "main/jobs", "job:42/photo:a") != null,
            "stable element context");
        String json = AnnotationRecords.toJson(reload, "2026-11-07T20:12:00Z");
        check(json.contains("\"schema\": \"accubook.annotations.v1\""), "schema");
        check(json.contains("\"annotation_count\": 2"), "count");
        check(json.contains("Jiggle then drop:\\nExpected \\\"move\\\" & keep"), "JSON escaping");
        check(json.contains("Use \\\\ backslash,\\t tab"), "JSON backslash and tab escaping");
        notes = AnnotationRecords.delete(notes, "main/jobs", "job:42/photo:a");
        check(notes.size() == 1, "delete only matching element");
        try {
            AnnotationRecords.read("wrong,columns\r\n");
            throw new AssertionError("unexpected schema accepted");
        } catch (IOException expected) { /* expected */ }
        try {
            AnnotationRecords.upsert(notes, "d", "main", "key", "/path", "Button",
                "label", "x".repeat(AnnotationRecords.MAX_NOTE + 1), "now");
            throw new AssertionError("oversized note accepted");
        } catch (IllegalArgumentException expected) { /* expected */ }
        System.out.println("AnnotationRecordsSmoke PASS");
    }
}
