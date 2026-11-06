package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** RFC 4180-compatible UTF-8 record codec; no spreadsheet formula evaluation. */
public final class CsvCodec {
    private CsvCodec() {}

    public static String write(List<List<String>> rows) {
        StringBuilder output = new StringBuilder();
        for (List<String> row : rows) {
            for (int i = 0; i < row.size(); i++) {
                if (i > 0) output.append(',');
                String value = row.get(i) == null ? "" : row.get(i);
                boolean quoted = value.indexOf(',') >= 0
                    || value.indexOf('"') >= 0
                    || value.indexOf('\r') >= 0
                    || value.indexOf('\n') >= 0;
                if (quoted) output.append('"');
                for (int j = 0; j < value.length(); j++) {
                    char ch = value.charAt(j);
                    if (ch == '"') output.append('"');
                    output.append(ch);
                }
                if (quoted) output.append('"');
            }
            output.append("\r\n");
        }
        return output.toString();
    }

    public static List<List<String>> read(String input) throws IOException {
        if (input == null || input.isEmpty()) return Collections.emptyList();
        int index = input.charAt(0) == '\uFEFF' ? 1 : 0;
        List<List<String>> rows = new ArrayList<>();
        List<String> row = new ArrayList<>();
        StringBuilder value = new StringBuilder();
        boolean quoted = false;
        boolean afterQuote = false;
        boolean freshField = true;
        for (; index < input.length(); index++) {
            char ch = input.charAt(index);
            if (quoted) {
                if (ch == '"') {
                    if (index + 1 < input.length() && input.charAt(index + 1) == '"') {
                        value.append('"');
                        index++;
                    } else {
                        quoted = false;
                        afterQuote = true;
                    }
                } else {
                    value.append(ch);
                }
                continue;
            }
            if (ch == ',' || ch == '\n' || ch == '\r') {
                row.add(value.toString());
                value.setLength(0);
                freshField = true;
                afterQuote = false;
                if (ch != ',') {
                    if (ch == '\r' && index + 1 < input.length()
                        && input.charAt(index + 1) == '\n') index++;
                    rows.add(row);
                    row = new ArrayList<>();
                }
            } else if (ch == '"' && freshField) {
                quoted = true;
                freshField = false;
            } else {
                if (afterQuote || ch == '"') throw new IOException("Invalid quoted CSV field");
                value.append(ch);
                freshField = false;
            }
        }
        if (quoted) throw new IOException("Unterminated quoted CSV field");
        if (!freshField || afterQuote || !row.isEmpty()) {
            row.add(value.toString());
            rows.add(row);
        }
        return rows;
    }
}
