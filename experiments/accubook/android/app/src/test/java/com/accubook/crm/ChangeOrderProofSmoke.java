package com.accubook.crm;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Portable proof/amount invariants, runnable without Android. */
public final class ChangeOrderProofSmoke {
    private static void check(boolean value,String reason){
        if(!value)throw new AssertionError(reason);
    }
    public static void main(String[] args){
        String id="CO-"+"c".repeat(32),lineId="COL-"+"d".repeat(32);
        List<List<String>> lines=new ArrayList<>();
        lines.add(new ArrayList<>(Arrays.asList(lineId,id,"Extra downspout",
            "2.5","24.00","60.00")));
        check(ChangeOrderProof.total(lines).equals("60.00"),"Wrong total");
        check(ChangeOrderProof.amount("2.5","24.00").equals("60.00"),"Wrong extended value");
        String sig=ChangeOrderProof.sha256("ink".getBytes(java.nio.charset.StandardCharsets.UTF_8));
        String first=ChangeOrderProof.contentHash("JOB-123",id,"Additional gutter work",
            "2026-11-07T19:00:00Z","Test Signer",sig,lines);
        check(first.equals(ChangeOrderProof.contentHash("JOB-123",id,
            "Additional gutter work","2026-11-07T19:00:00Z","Test Signer",sig,lines)),
            "Hash not deterministic");
        lines.get(0).set(2,"Different work");
        check(!first.equals(ChangeOrderProof.contentHash("JOB-123",id,
            "Additional gutter work","2026-11-07T19:00:00Z","Test Signer",sig,lines)),
            "Tampered description retained original proof");
        lines.get(0).set(2,"Extra downspout");
        check(!first.equals(ChangeOrderProof.contentHash("JOB-123",id,
            "Additional gutter work","2026-11-07T19:00:00Z","Another signer",sig,lines)),
            "Tampered signer retained original proof");
        boolean bad=false;
        lines.get(0).set(5,"999.00");
        try{ChangeOrderProof.total(lines);}catch(IllegalArgumentException expected){bad=true;}
        check(bad,"Altered line amount was accepted");
        System.out.println("ChangeOrderProofSmoke: PASS");
    }
}