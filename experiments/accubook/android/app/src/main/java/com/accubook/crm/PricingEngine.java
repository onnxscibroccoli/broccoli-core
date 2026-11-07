package com.accubook.crm;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Portable, deterministic field-to-invoice pricing; no runtime web or AI. */
public final class PricingEngine {
    private PricingEngine(){}
    public static BigDecimal price(BigDecimal baseCost,BigDecimal markupPercent){
        if(baseCost==null||markupPercent==null||baseCost.signum()<0||
            baseCost.compareTo(new BigDecimal("1000000"))>0||
            markupPercent.compareTo(new BigDecimal("-100"))<0||
            markupPercent.compareTo(new BigDecimal("1000"))>0)
            throw new IllegalArgumentException("Invalid base cost or markup");
        return baseCost.multiply(BigDecimal.ONE.add(markupPercent.movePointLeft(2)))
            .setScale(2,RoundingMode.HALF_UP);
    }
    public static BigDecimal extended(BigDecimal quantity,BigDecimal unitPrice){
        if(quantity==null||unitPrice==null||quantity.signum()<=0||
            quantity.compareTo(new BigDecimal("1000000"))>0)
            throw new IllegalArgumentException("Invalid quantity");
        return unitPrice.multiply(quantity).setScale(2,RoundingMode.HALF_UP);
    }
}
