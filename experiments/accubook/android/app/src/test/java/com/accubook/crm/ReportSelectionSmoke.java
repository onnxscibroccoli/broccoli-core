package com.accubook.crm;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;

/** Standalone regression: exclusions must never leak disallowed payment channels. */
public final class ReportSelectionSmoke {
    private static void check(boolean ok,String why){
        if(!ok)throw new AssertionError(why);
    }
    private static void fails(Runnable action,String name){
        try{action.run();throw new AssertionError("Accepted invalid "+name);}
        catch(IllegalArgumentException expected){}
    }
    public static void main(String[] args){
        boolean[] sections={false,true,false,false,false,false};
        ReportSelection jobs=new ReportSelection(sections,
            Collections.emptySet(),Collections.emptySet());
        sections[1]=false;
        check(jobs.include(1),"caller mutation changed section");
        check(!jobs.include(3),"jobs-only report leaked payment section");
        check(!jobs.payment("Cash App"),"jobs-only report leaked Cash App");
        check(!jobs.expense("Tools"),"jobs-only report leaked expense");

        boolean[] selective={false,false,false,true,true,false};
        ReportSelection selected=new ReportSelection(selective,
            new LinkedHashSet<>(Arrays.asList("Cash","Check")),
            new LinkedHashSet<>(Arrays.asList("Materials","Fuel")));
        check(selected.payment("Cash"),"cash selected");
        check(!selected.payment("Cash App"),"Cash App must be excluded");
        check(!selected.payment("PayPal"),"PayPal must be excluded");
        check(selected.expense("Fuel"),"Fuel selected");
        check(!selected.expense("Mileage"),"Mileage must be excluded");
        boolean[] copy=selected.sections();copy[3]=false;
        check(selected.include(3),"returned sections are not immutable");
        fails(()->selected.methods().add("Cash App"),"mutable payment allow-list");
        fails(()->selected.categories().add("Mileage"),"mutable expense allow-list");

        fails(()->new ReportSelection(new boolean[6],
            Collections.emptySet(),Collections.emptySet()),"empty report");
        fails(()->new ReportSelection(new boolean[]{false,false,false,true,false,false},
            Collections.emptySet(),Collections.emptySet()),"unfiltered payments");
        fails(()->new ReportSelection(new boolean[]{false,false,false,false,true,false},
            Collections.emptySet(),Collections.emptySet()),"unfiltered expenses");
        fails(()->new ReportSelection(new boolean[]{true,false,false,false,false,false},
            Collections.singleton("SecretMethod"),Collections.emptySet()),"unknown method");
        fails(()->new ReportSelection(new boolean[]{true},Collections.emptySet(),
            Collections.emptySet()),"invalid number of sections");
        System.out.println("ReportSelectionSmoke PASS");
    }
}
