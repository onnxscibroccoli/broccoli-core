package com.accubook.crm;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;

/** Dependency-free safeguards against accidentally leaking excluded ledgers. */
public final class ExportSelectionSmoke {
    private static void check(boolean condition,String message){
        if(!condition)throw new AssertionError(message);
    }
    public static void main(String[] args){
        boolean[] choose=new boolean[ExportSelection.SECTION_COUNT];
        boolean rejected=false;
        try{new ExportSelection(choose,Set.of(),Set.of());}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"Nothing selected should fail closed");

        choose[3]=true;choose[4]=true;
        rejected=false;
        try{new ExportSelection(choose,Set.of(),Set.of());}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"Payments and expenses must explicitly select ledgers");

        Set<String> ledgers=new LinkedHashSet<>(Arrays.asList("Cash","Cash App"));
        Set<String> categories=new LinkedHashSet<>(Arrays.asList("Fuel","Tools"));
        ExportSelection filter=new ExportSelection(choose,ledgers,categories);
        ledgers.add("Bank Transfer");
        categories.add("Meals");
        choose[1]=true;
        check(filter.includesPayment("Cash"),"Cash excluded accidentally");
        check(filter.includesPayment("Cash App"),"Cash App excluded accidentally");
        check(!filter.includesPayment("Bank Transfer"),
            "New ledger leaked through mutable caller reference");
        check(filter.includesExpense("Fuel"),"Fuel excluded accidentally");
        check(!filter.includesExpense("Meals"),
            "New category leaked through mutable caller reference");
        check(!filter.sections[1],"Selected sections mutated by caller");
        try{filter.paymentMethods.add("Other");throw new AssertionError("Mutable export scope");}
        catch(UnsupportedOperationException expected){}
        System.out.println("ExportSelectionSmoke: PASS (fail-closed, selected ledgers, isolation)");
    }
}
