package com.accubook.crm;

import java.io.IOException;
import java.util.List;

/** Stable-row CSV ordering; the header remains fixed and amounts never change. */
public final class InvoiceLineOrdering {
    private InvoiceLineOrdering(){}
    public static boolean move(List<List<String>> rows,String id,int position)
        throws IOException {
        if(rows==null||rows.isEmpty()||!rows.get(0).equals(
            java.util.Arrays.asList("ItemID","Description","Quantity","UnitRate","LineTotal")))
            throw new IOException("Unrecognized invoice line schema");
        int count=rows.size()-1;
        if(position<0||position>=count)throw new IOException("Invalid line destination");
        int from=-1;
        java.util.HashSet<String> ids=new java.util.HashSet<>();
        for(int i=1;i<rows.size();i++){
            List<String> r=rows.get(i);
            if(r.size()!=5||!ids.add(r.get(0)))
                throw new IOException("Invalid or repeated invoice line");
            if(r.get(0).equals(id))from=i;
        }
        if(from<0)throw new IOException("Invoice line not found");
        int to=position+1;
        if(from==to)return false;
        List<String> selected=rows.remove(from);
        rows.add(to,selected);
        return true;
    }
}
