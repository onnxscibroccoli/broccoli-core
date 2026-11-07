package com.accubook.crm;

import java.math.BigDecimal;

/** JVM acceptance of trade pricing and safe customer document IDs. */
public final class PricingEngineSmoke {
    private static void equal(String expected,String actual){
        if(!expected.equals(actual))throw new AssertionError(expected+" != "+actual);
    }
    public static void main(String[] args){
        equal("250.00",PricingEngine.price(new BigDecimal("250.00"),
            BigDecimal.ZERO).toPlainString());
        equal("50.00",PricingEngine.price(new BigDecimal("50.00"),
            BigDecimal.ZERO).toPlainString());
        equal("10.00",PricingEngine.price(new BigDecimal("10"),
            BigDecimal.ZERO).toPlainString());
        equal("56.25",PricingEngine.price(new BigDecimal("45"),new BigDecimal("25"))
            .toPlainString());
        equal("112.50",PricingEngine.extended(new BigDecimal("2"),
            new BigDecimal("56.25")).toPlainString());
        boolean invalid=false;
        try{PricingEngine.price(new BigDecimal("-1"),BigDecimal.ZERO);}
        catch(IllegalArgumentException expected){invalid=true;}
        if(!invalid)throw new AssertionError("Negative costs accepted");
        String job="JOB-0123456789abcdef0123456789abcdef";
        String estimate=DocumentNumbers.reference(job,"2026-11-07",true);
        String invoice=DocumentNumbers.reference(job,"2027-01-01",false);
        if(estimate.contains(job)||estimate.contains("0123456")||
            !estimate.matches("EST-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}"))
            throw new AssertionError("Internal ID exposed in document reference");
        equal(invoice,DocumentNumbers.reference(job,"2030-12-31",false));
        equal(estimate.substring(4),invoice.substring(4));
        System.out.println("PricingEngineSmoke: PASS (markup, extensions, stable human IDs)");
    }
}
