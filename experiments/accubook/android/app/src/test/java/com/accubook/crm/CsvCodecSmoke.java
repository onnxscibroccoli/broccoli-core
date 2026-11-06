package com.accubook.crm;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;

/** No external test dependencies: run with javac/java on CI and Termux. */
public final class CsvCodecSmoke {
    private CsvCodecSmoke() {}

    private static void check(boolean condition, String failure) {
        if (!condition) throw new AssertionError(failure);
    }

    public static void main(String[] args) throws Exception {
        List<List<String>> source = Arrays.asList(
            Arrays.asList("CustomerID", "Name", "Notes"),
            Arrays.asList("CUST-1001", "Acme, Inc.", "One\r\nTwo"),
            Arrays.asList("CUST-1002", "A \"quoted\" name", ""),
            Arrays.asList("CUST-1003", "Unicode café ☕", "last")
        );
        check(CsvCodec.read(CsvCodec.write(source)).equals(source), "CSV roundtrip");
        check(CsvCodec.read("\uFEFFa,b\r\nx,y\r\n").size() == 2, "UTF-8 BOM");
        check(CsvCodec.read("x,y\n1,2").size() == 2, "LF and final row");
        boolean threw = false;
        try { CsvCodec.read("a,\"unfinished"); } catch (IOException expected) { threw = true; }
        check(threw, "Reject unterminated quoted field");
        threw = false;
        try { CsvCodec.read("a,\"ok\"trailing"); } catch (IOException expected) { threw = true; }
        check(threw, "Reject invalid CSV field");
        System.out.println("CSV CODEC PASS: 5 assertions");
    }
}
