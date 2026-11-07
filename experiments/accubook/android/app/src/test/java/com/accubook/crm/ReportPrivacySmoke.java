package com.accubook.crm;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** Dependency-free JVM regression: no indirect leakage from filtered payment ledgers. */
public final class ReportPrivacySmoke {
    private static final class Row {
        final String method;
        final String amount;
        Row(String method, String amount) { this.method=method; this.amount=amount; }
    }
    private static BigDecimal sum(List<Row> rows, Set<String> methods) {
        return ReportPrivacy.selectedReceipts(rows, methods, r->r.method, r->r.amount);
    }
    private static void equal(String expected, BigDecimal actual) {
        if (new BigDecimal(expected).compareTo(actual)!=0)
            throw new AssertionError("expected="+expected+" actual="+actual);
    }
    public static void main(String[] args) {
        List<Row> rows=Arrays.asList(
            new Row("Cash","110.00"),
            new Row("Cash App","350.00"),
            new Row("Card","25.00"),
            new Row("Card","15.00"));
        equal("0.00",sum(rows,Collections.emptySet()));
        equal("40.00",sum(rows,Collections.singleton("Card")));
        equal("350.00",sum(rows,Collections.singleton("Cash App")));
        equal("390.00",sum(rows,new LinkedHashSet<>(
            Arrays.asList("Cash App","Card"))));
        equal("500.00",new BigDecimal("500.00").subtract(
            sum(rows,Collections.emptySet())));
        equal("460.00",new BigDecimal("500.00").subtract(
            sum(rows,Collections.singleton("Card"))));
        // Invalid monetary values in excluded ledgers must never be parsed.
        equal("40.00",sum(Arrays.asList(new Row("Cash","not-a-number"),
            new Row("Card","40.00")), Collections.singleton("Card")));
        System.out.println("ReportPrivacySmoke: PASS (opt-in methods, excluded cash and Cash App)");
    }
}
