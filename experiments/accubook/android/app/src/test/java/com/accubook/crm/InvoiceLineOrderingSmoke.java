package com.accubook.crm;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Moving billable lines cannot change amounts, IDs, or header. */
public final class InvoiceLineOrderingSmoke {
    private static List<String> r(String... v){return new ArrayList<>(Arrays.asList(v));}
    private static void check(boolean ok,String msg){if(!ok)throw new AssertionError(msg);}
    public static void main(String[] args)throws Exception{
        List<List<String>> rows=new ArrayList<>();
        rows.add(r("ItemID","Description","Quantity","UnitRate","LineTotal"));
        rows.add(r("A","Labor","2","45.00","90.00"));
        rows.add(r("B","Material","3","6.00","18.00"));
        rows.add(r("C","Discount","1","-5.00","-5.00"));
        check(InvoiceLineOrdering.move(rows,"A",2),"Expected move");
        check(rows.get(1).get(0).equals("B")&&rows.get(2).get(0).equals("C")&&
            rows.get(3).get(0).equals("A"),"Stable ordering failed");
        check(rows.get(3).get(4).equals("90.00"),"Moving a line changed money");
        check(!InvoiceLineOrdering.move(rows,"A",2),"No-op move should not rewrite");
        boolean rejected=false;
        try{InvoiceLineOrdering.move(rows,"A",3);}
        catch(java.io.IOException expected){rejected=true;}
        check(rejected,"Out-of-range line index was accepted");
        rows.add(r("A","Conflicting","1","1.00","1.00"));
        rejected=false;
        try{InvoiceLineOrdering.move(rows,"C",0);}
        catch(java.io.IOException expected){rejected=true;}
        check(rejected,"Duplicate invoice IDs were accepted");
        System.out.println("InvoiceLineOrderingSmoke: PASS");
    }
}