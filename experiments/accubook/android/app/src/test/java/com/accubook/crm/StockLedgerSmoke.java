package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Pure JVM, deterministic company/job/tool stock reconciliation tests. */
public final class StockLedgerSmoke {
    private static final String ITEM="INV-"+"1".repeat(32),
        TOOLID="INV-"+"2".repeat(32),JOB="JOB-"+"a".repeat(32);
    private static List<String> row(String...values){
        return new ArrayList<>(Arrays.asList(values));
    }
    private static List<List<String>> items(){
        List<List<String>> rows=new ArrayList<>();
        rows.add(row(StockLedger.ITEMS));
        rows.add(row(ITEM,"Shingles","MATERIAL","bundle","true"));
        rows.add(row(TOOLID,"Roof ladder","TOOL","each","true"));
        return rows;
    }
    private static List<List<String>> ledger(){
        List<List<String>> rows=new ArrayList<>();
        rows.add(row(StockLedger.MOVES));
        return rows;
    }
    private static void event(List<List<String>> rows,int n,String item,String action,
                              String from,String to,String qty,String note){
        rows.add(row("MOVE-"+Integer.toHexString(n).repeat(32),
            item,"2026-11-07T19:10:00Z",action,from,to,qty,note));
    }
    private static StockLedger.State state(List<List<String>> items,List<List<String>> events)
        throws IOException {
        return StockLedger.validate(items,events,new HashSet<>(Arrays.asList(JOB)));
    }
    private static void check(boolean ok,String reason){if(!ok)throw new AssertionError(reason);}
    private static void rejects(List<List<String>> items,List<List<String>> events,
                                String reason)throws Exception{
        boolean refused=false;
        try{state(items,events);}catch(IOException expected){refused=true;}
        check(refused,reason);
    }
    public static void main(String[] args)throws Exception {
        List<List<String>> items=items(),events=ledger();
        event(events,1,ITEM,StockLedger.RECEIVE,StockLedger.EXTERNAL,
            StockLedger.COMPANY,"10","Delivery received");
        event(events,2,ITEM,StockLedger.TRANSFER,StockLedger.COMPANY,JOB,"6","To site");
        event(events,3,ITEM,StockLedger.USE,JOB,StockLedger.CONSUMED,"2","Installed");
        event(events,4,ITEM,StockLedger.TRANSFER,JOB,StockLedger.COMPANY,"1","Unused returned");
        event(events,5,TOOLID,StockLedger.RECEIVE,StockLedger.EXTERNAL,
            StockLedger.COMPANY,"1","Ladder acquired");
        event(events,6,TOOLID,StockLedger.TRANSFER,StockLedger.COMPANY,JOB,"1","Checked out");
        StockLedger.State current=state(items,events);
        check(current.balance(ITEM,StockLedger.COMPANY).intValueExact()==5,
            "Company stock not reconciled");
        check(current.balance(ITEM,JOB).intValueExact()==3,
            "Job site stock not reconciled");
        check(current.balance(TOOLID,JOB).intValueExact()==1,
            "Tool checkout missing");
        check(current.balance(TOOLID,StockLedger.COMPANY).signum()==0,
            "Tool exists in two locations");
        event(events,7,ITEM,StockLedger.TRANSFER,JOB,StockLedger.COMPANY,
            "4","Too much");
        rejects(items,events,"Negative job stock accepted");
        events.remove(events.size()-1);
        event(events,7,TOOLID,StockLedger.USE,JOB,StockLedger.CONSUMED,"1","Tool used");
        rejects(items,events,"Tool was consumed as material");
        events.remove(events.size()-1);
        event(events,7,TOOLID,StockLedger.TRANSFER,JOB,StockLedger.COMPANY,
            "0.5","Half tool");
        rejects(items,events,"Fractional tools accepted");
        events.remove(events.size()-1);
        event(events,7,ITEM,StockLedger.TRANSFER,StockLedger.COMPANY,
            "JOB-"+"b".repeat(32),"1","Unknown site");
        rejects(items,events,"Orphaned job references accepted");
        events.remove(events.size()-1);
        event(events,7,ITEM,StockLedger.ADJUST_OUT,StockLedger.COMPANY,
            StockLedger.EXTERNAL,"1","");
        rejects(items,events,"Unexplained loss accepted");
        events.remove(events.size()-1);
        event(events,7,ITEM,StockLedger.ADJUST_OUT,StockLedger.COMPANY,
            StockLedger.EXTERNAL,"1","Physical count");
        check(state(items,events).balance(ITEM,StockLedger.COMPANY).intValueExact()==4,
            "Corrected company stock wrong");
        events.add(new ArrayList<>(events.get(events.size()-1)));
        rejects(items,events,"Repeated movement ID double-counted stock");
        events.remove(events.size()-1);
        items.add(new ArrayList<>(items.get(1)));
        rejects(items,events,"Duplicate item id accepted");
        items.remove(items.size()-1);
        List<List<String>> bad=ledger();
        event(bad,1,ITEM,StockLedger.RECEIVE,StockLedger.EXTERNAL,
            StockLedger.COMPANY,"NaN","bad");
        rejects(items,bad,"Invalid stock number accepted");
        check(state(items,events).movements.size()==7,"Unexpected event history");
        System.out.println("StockLedgerSmoke: PASS");
    }
}
