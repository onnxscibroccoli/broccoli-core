package com.accubook.crm;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Pure Java, single-event offline stock ledger. The three human views (company
 * stock, job-site stock, tools) derive from ONE immutable movement history.
 * Transfers debit and credit together in one atomic CSV row, never via two
 * independently committed balances. This is not financial accounting.
 */
public final class StockLedger {
    public static final String[] ITEMS={"ItemID","Name","Kind","Unit","Active"};
    public static final String[] MOVES={"MovementID","ItemID","OccurredUTC","Action",
        "FromLocation","ToLocation","Quantity","Reason"};
    public static final String MATERIAL="MATERIAL", TOOL="TOOL";
    public static final String COMPANY="COMPANY",EXTERNAL="EXTERNAL",CONSUMED="CONSUMED";
    public static final String RECEIVE="RECEIVE", TRANSFER="TRANSFER",
        USE="USE",ADJUST_IN="ADJUST_IN",ADJUST_OUT="ADJUST_OUT";
    public static final class Item {
        public final String id,name,kind,unit;
        public final boolean active;
        public Item(List<String> row){
            id=row.get(0);name=row.get(1);kind=row.get(2);unit=row.get(3);
            active=Boolean.parseBoolean(row.get(4));
        }
    }
    public static final class Movement {
        public final String id,itemId,time,action,from,to,quantity,reason;
        public Movement(List<String> r){
            id=r.get(0);itemId=r.get(1);time=r.get(2);action=r.get(3);
            from=r.get(4);to=r.get(5);quantity=r.get(6);reason=r.get(7);
        }
    }
    public static final class State {
        public final List<Item> items;
        public final List<Movement> movements;
        private final Map<String,BigDecimal> balances;
        State(List<Item> items,List<Movement> movements,Map<String,BigDecimal> balances){
            this.items=java.util.Collections.unmodifiableList(items);
            this.movements=java.util.Collections.unmodifiableList(movements);
            this.balances=balances;
        }
        public BigDecimal balance(String itemId,String location){
            return balances.getOrDefault(itemId+"/"+location,BigDecimal.ZERO);
        }
    }
    private StockLedger(){}
    private static void valid(boolean okay,String problem) throws IOException {
        if(!okay)throw new IOException("Inventory: "+problem);
    }
    private static void grid(List<List<String>> data,String[] headers,String label)throws IOException{
        valid(data!=null&&!data.isEmpty()&&data.get(0).equals(Arrays.asList(headers)),
            "unknown "+label+" file schema");
        valid(data.size()<=10001,"too many "+label+" records");
        for(List<String> row:data)
            valid(row.size()==headers.length,"invalid "+label+" row width");
    }
    public static BigDecimal quantity(String entered,String kind) throws IOException {
        BigDecimal q;
        try{q=new BigDecimal(entered);}
        catch(Exception e){throw new IOException("Enter a valid stock quantity",e);}
        valid(q.signum()>0 && q.compareTo(new BigDecimal("1000000"))<=0
            && q.scale()<=3 && q.scale()>=0,"positive quantity with up to 3 decimals required");
        if(TOOL.equals(kind))valid(q.stripTrailingZeros().scale()<=0,
            "tool count must be whole units");
        return q;
    }
    private static String trim(String raw,int max,String field)throws IOException{
        valid(raw!=null,"missing "+field);
        String v=raw.trim();
        valid(v.length()>0&&v.length()<=max&&v.indexOf('\0')<0,
            "invalid "+field);
        return v;
    }
    private static boolean site(String location,Set<String> existingJobs){
        return location.matches("JOB-[a-f0-9]{32}")&&existingJobs.contains(location);
    }
    /** Read, validate all references and events in order, and derive nonnegative stock. */
    public static State validate(List<List<String>> itemRows,List<List<String>> movements,
                                 Set<String> validJobs) throws IOException {
        grid(itemRows,ITEMS,"items");
        grid(movements,MOVES,"movements");
        valid(validJobs!=null,"missing job index");
        List<Item> items=new ArrayList<>();
        Map<String,Item> lookup=new HashMap<>();
        for(int i=1;i<itemRows.size();i++){
            Item item=new Item(itemRows.get(i));
            valid(item.id.matches("INV-[a-f0-9]{32}")&&!lookup.containsKey(item.id),
                "invalid or repeated item id");
            trim(item.name,180,"item name");
            trim(item.unit,40,"unit");
            valid(Arrays.asList(MATERIAL,TOOL).contains(item.kind),"unknown item kind");
            valid(Arrays.asList("true","false").contains(itemRows.get(i).get(4)),
                "invalid item active state");
            items.add(item);lookup.put(item.id,item);
        }
        Map<String,BigDecimal> count=new HashMap<>();
        List<Movement> entries=new ArrayList<>();
        Set<String> usedIds=new HashSet<>();
        for(int i=1;i<movements.size();i++){
            Movement m=new Movement(movements.get(i));
            valid(m.id.matches("MOVE-[a-f0-9]{32}")&&usedIds.add(m.id),
                "invalid or duplicate movement id");
            Item item=lookup.get(m.itemId);
            valid(item!=null,"orphaned item movement");
            try{Instant.parse(m.time);}
            catch(Exception e){throw new IOException("Inventory: invalid UTC timestamp",e);}
            valid(m.reason.length()<=250&&m.reason.indexOf('\0')<0,"reason too long");
            BigDecimal q=quantity(m.quantity,item.kind);
            boolean fromStock=m.from.equals(COMPANY)||site(m.from,validJobs);
            boolean toStock=m.to.equals(COMPANY)||site(m.to,validJobs);
            valid(!m.from.equals(m.to),"movement cannot return to same location");
            if(RECEIVE.equals(m.action)){
                valid(m.from.equals(EXTERNAL)&&m.to.equals(COMPANY),
                    "received stock must enter company inventory");
            }else if(TRANSFER.equals(m.action)){
                valid(fromStock&&toStock,"transfer needs existing stock locations");
            }else if(USE.equals(m.action)){
                valid(item.kind.equals(MATERIAL)&&site(m.from,validJobs)&&m.to.equals(CONSUMED),
                    "only job-site material can be consumed");
            }else if(ADJUST_IN.equals(m.action)){
                valid(m.from.equals(EXTERNAL)&&m.to.equals(COMPANY)
                    &&!m.reason.trim().isEmpty(),"adjustment in needs a reason");
            }else if(ADJUST_OUT.equals(m.action)){
                valid(m.from.equals(COMPANY)&&m.to.equals(EXTERNAL)
                    &&!m.reason.trim().isEmpty(),"adjustment out needs a reason");
            }else throw new IOException("Inventory: unknown movement action");
            if(fromStock){
                String key=m.itemId+"/"+m.from;
                BigDecimal remaining=count.getOrDefault(key,BigDecimal.ZERO).subtract(q);
                valid(remaining.signum()>=0,"negative stock or duplicate movement at "+m.from);
                count.put(key,remaining);
            }
            if(toStock){
                String key=m.itemId+"/"+m.to;
                count.put(key,count.getOrDefault(key,BigDecimal.ZERO).add(q));
            }
            entries.add(m);
        }
        return new State(items,entries,count);
    }
}
