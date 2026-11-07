package com.accubook.crm;

import java.util.Arrays;
import java.util.List;

/** Standalone, deterministic inventory safety tests (no Android dependency). */
public final class InventoryRulesSmoke {
    private static void check(boolean value,String why) {
        if(!value)throw new AssertionError(why);
    }
    private static void reject(Runnable action,String why) {
        boolean failed=false;
        try{action.run();}catch(IllegalArgumentException expected){failed=true;}
        check(failed,why);
    }
    private static List<String> row(String... values){return Arrays.asList(values);}
    public static void main(String[] ignored){
        String mid="MAT-"+"a".repeat(32), sid="SITE-"+"b".repeat(32),
            tid="TOOL-"+"c".repeat(32), jid="JOB-"+"d".repeat(32),
            catalog="CAT-"+"e".repeat(32);
        check("1.5".equals(InventoryRules.quantity("01.5000",false)),"Quantity normalized");
        check("0".equals(InventoryRules.quantity("0",true)),"Empty stock allowed");
        check("12.30".equals(InventoryRules.cost("12.3")),"Cost normalized");
        reject(()->InventoryRules.quantity("0",false),"Zero site usage disallowed");
        reject(()->InventoryRules.quantity("-1",true),"Negative stock rejected");
        reject(()->InventoryRules.quantity("0.00001",false),"Excess quantity precision");
        reject(()->InventoryRules.cost("0.001"),"Excess currency precision");
        reject(()->InventoryRules.cost("-0.01"),"Negative unit cost");
        reject(()->InventoryRules.text("Name\nInjected",160,true),"Control chars");
        InventoryRules.company(row(mid,"Shingle","bundle","3.5","28.00",catalog));
        InventoryRules.site(row(sid,"Shingle","bundle","2","Delivered"));
        InventoryRules.tool(row(tid,"Ladder","TAG-001","Checked Out",jid));
        InventoryRules.tool(row(tid,"Ladder","","Available",""));
        reject(()->InventoryRules.company(row(mid,"Shingle","bundle","-1","28.00","")),
            "Invalid stock is rejected");
        reject(()->InventoryRules.company(row(mid,"Shingle","bundle","2","28.0","")),
            "Noncanonical cost is rejected before backup restore");
        reject(()->InventoryRules.site(row(sid,"Shingle","bundle","2","Billed")),
            "Unrecognized state");
        reject(()->InventoryRules.site(row(sid,"Shingle","bundle","0","Used")),
            "Zero site quantity");
        reject(()->InventoryRules.tool(row(tid,"Ladder","","Checked Out","")),
            "Checked-out item requires a job");
        reject(()->InventoryRules.tool(row(tid,"Ladder","","Available",jid)),
            "Available tools must not remain assigned");
        System.out.println("InventoryRulesSmoke PASS");
    }
}
