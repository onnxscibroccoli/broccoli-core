package com.accubook.crm;

import java.math.BigDecimal;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;

/**
 * Safe monetary aggregation for explicit accounting export allow-lists.
 * Excluded payment methods MUST NOT contribute to derived totals or balances.
 * Kept Android-free so the rule can be tested independently of the user interface.
 */
public final class ReportPrivacy {
    private ReportPrivacy() {}

    public static <T> BigDecimal selectedReceipts(
        Iterable<T> payments, Set<String> allowedMethods,
        Function<T, String> method, Function<T, String> amount) {
        Objects.requireNonNull(payments, "payments");
        Objects.requireNonNull(allowedMethods, "allowedMethods");
        Objects.requireNonNull(method, "method");
        Objects.requireNonNull(amount, "amount");
        BigDecimal total = BigDecimal.ZERO;
        for (T payment : payments) {
            // Do not inspect the amount of an excluded record.
            if (allowedMethods.contains(method.apply(payment))) {
                total = total.add(new BigDecimal(amount.apply(payment)));
            }
        }
        return total;
    }
}
