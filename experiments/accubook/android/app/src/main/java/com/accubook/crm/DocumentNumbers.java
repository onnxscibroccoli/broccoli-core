package com.accubook.crm;

import java.math.BigInteger;
import java.time.LocalDate;

/**
 * Customer-facing, portable deterministic reference. Never leaks a raw internal UUID.
 * Not a substitute for a jurisdiction-specific sequential tax invoice numbering system.
 */
public final class DocumentNumbers {
    private DocumentNumbers() {}

    public static String reference(String jobId, String date, boolean estimate) {
        if (jobId == null || !jobId.matches("JOB-[0-9a-f]{32}"))
            throw new IllegalArgumentException("Invalid job reference");
        int year = LocalDate.parse(date).getYear();
        // 10 decimal digits, stable across backups without another side table.
        // Collision detection/sequential issued numbers remain a release requirement.
        long suffix = new BigInteger(jobId.substring(4), 16)
            .mod(BigInteger.valueOf(10_000_000_000L)).longValue();
        return (estimate ? "EST-" : "INV-") + year + "-" +
            String.format(java.util.Locale.ROOT, "%010d", suffix);
    }
}
