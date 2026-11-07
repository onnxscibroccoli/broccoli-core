package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Versioned, local-only development annotations. Portable CSV on disk, JSON only
 * when the owner explicitly exports it. No network, analytics or device identifiers.
 */
public final class AnnotationRecords {
    public static final int MAX_RECORDS = 1000;
    public static final int MAX_NOTE = 4000;
    private static final List<String> HEADER = Collections.unmodifiableList(Arrays.asList(
        "id", "screen", "element_key", "element_path", "widget", "label",
        "note", "created_utc", "updated_utc"));

    private AnnotationRecords() {}

    public static final class Entry {
        public final String id, screen, key, path, widget, label, note, created, updated;
        public Entry(String id, String screen, String key, String path, String widget,
                String label, String note, String created, String updated) {
            this.id = valid(id, 80, "id");
            this.screen = valid(screen, 180, "screen");
            this.key = valid(key, 300, "element key");
            this.path = valid(path, 500, "element path");
            this.widget = valid(widget, 100, "widget");
            this.label = bounded(label, 200, "label");
            this.note = valid(note, MAX_NOTE, "note");
            this.created = valid(created, 50, "creation time");
            this.updated = valid(updated, 50, "update time");
        }
        List<String> row() {
            return Arrays.asList(id, screen, key, path, widget, label, note, created, updated);
        }
    }

    private static String bounded(String value, int max, String name) {
        if (value == null || value.length() > max)
            throw new IllegalArgumentException("Invalid " + name + " length");
        if (value.indexOf('\u0000') >= 0)
            throw new IllegalArgumentException(name + " contains a null character");
        return value;
    }
    private static String valid(String value, int max, String name) {
        bounded(value, max, name);
        if (value.trim().isEmpty()) throw new IllegalArgumentException(name + " is empty");
        return value;
    }

    public static List<Entry> read(String csv) throws IOException {
        if (csv == null || csv.isEmpty()) return new ArrayList<>();
        List<List<String>> rows = CsvCodec.read(csv);
        if (rows.isEmpty() || !HEADER.equals(rows.get(0)))
            throw new IOException("Unrecognized annotations file format");
        if (rows.size() - 1 > MAX_RECORDS) throw new IOException("Too many annotations");
        List<Entry> entries = new ArrayList<>();
        for (int n = 1; n < rows.size(); n++) {
            List<String> row = rows.get(n);
            if (row.size() != HEADER.size())
                throw new IOException("Invalid annotation column count at row " + (n + 1));
            try {
                Entry e = new Entry(row.get(0), row.get(1), row.get(2), row.get(3),
                    row.get(4), row.get(5), row.get(6), row.get(7), row.get(8));
                if (find(entries, e.screen, e.key) != null)
                    throw new IOException("Duplicate annotated element at row " + (n + 1));
                entries.add(e);
            } catch (IllegalArgumentException error) {
                throw new IOException("Invalid annotation at row " + (n + 1), error);
            }
        }
        return entries;
    }

    public static String write(List<Entry> entries) {
        if (entries.size() > MAX_RECORDS) throw new IllegalArgumentException("Too many annotations");
        List<List<String>> rows = new ArrayList<>();
        rows.add(HEADER);
        for (Entry e : entries) rows.add(e.row());
        return CsvCodec.write(rows);
    }

    public static Entry find(List<Entry> entries, String screen, String key) {
        for (Entry e : entries) if (e.screen.equals(screen) && e.key.equals(key)) return e;
        return null;
    }

    public static List<Entry> upsert(List<Entry> entries, String newId, String screen,
            String key, String path, String widget, String label, String note, String now) {
        Entry previous = find(entries, screen, key);
        Entry next = new Entry(previous == null ? newId : previous.id, screen, key, path,
            widget, label, note, previous == null ? now : previous.created, now);
        List<Entry> output = new ArrayList<>();
        for (Entry e : entries) if (!(e.screen.equals(screen) && e.key.equals(key))) output.add(e);
        if (output.size() >= MAX_RECORDS)
            throw new IllegalArgumentException("Annotation limit reached; export or remove notes");
        output.add(next);
        return output;
    }

    public static List<Entry> delete(List<Entry> entries, String screen, String key) {
        List<Entry> output = new ArrayList<>();
        for (Entry e : entries) if (!(e.screen.equals(screen) && e.key.equals(key))) output.add(e);
        return output;
    }

    private static String json(String s) {
        StringBuilder result = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': result.append("\\\""); break;
                case '\\': result.append("\\\\"); break;
                case '\n': result.append("\\n"); break;
                case '\r': result.append("\\r"); break;
                case '\t': result.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        String hex = Integer.toHexString(c);
                        result.append("\\u");
                        for (int j = hex.length(); j < 4; j++) result.append('0');
                        result.append(hex);
                    } else result.append(c);
            }
        }
        return result.append('"').toString();
    }

    public static String toJson(List<Entry> entries, String exportedUtc) {
        StringBuilder result = new StringBuilder();
        result.append("{\n  \"schema\": \"accubook.annotations.v1\",");
        result.append("\n  \"generated_utc\": ").append(json(exportedUtc)).append(",");
        result.append("\n  \"source\": \"local_user_annotations\",");
        result.append("\n  \"annotation_count\": ").append(entries.size()).append(",");
        result.append("\n  \"annotations\": [");
        for (int i = 0; i < entries.size(); i++) {
            Entry e = entries.get(i);
            result.append(i == 0 ? "\n" : ",\n");
            result.append("    {");
            result.append("\"id\": ").append(json(e.id));
            result.append(", \"screen\": ").append(json(e.screen));
            result.append(", \"element_key\": ").append(json(e.key));
            result.append(", \"element_path\": ").append(json(e.path));
            result.append(", \"widget\": ").append(json(e.widget));
            result.append(", \"label\": ").append(json(e.label));
            result.append(", \"note\": ").append(json(e.note));
            result.append(", \"created_utc\": ").append(json(e.created));
            result.append(", \"updated_utc\": ").append(json(e.updated));
            result.append("}");
        }
        if (!entries.isEmpty()) result.append("\n  ");
        return result.append("]\n}\n").toString();
    }
}
