package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Stable-id ordering that never moves inactive/tombstoned records. */
public final class FieldOrdering {
    private FieldOrdering(){}
    public static boolean moveActive(List<List<String>> rows,String fieldId,
                                     int newIndex,int activeColumn)throws IOException {
        if(rows==null||rows.isEmpty()||fieldId==null||activeColumn<0)
            throw new IOException("Invalid field order input");
        List<Integer> slots=new ArrayList<>();
        List<List<String>> active=new ArrayList<>();
        Set<String> ids=new HashSet<>();
        for(int i=1;i<rows.size();i++){
            List<String> row=rows.get(i);
            if(row.size()<=activeColumn)
                throw new IOException("Malformed field row");
            if(!ids.add(row.get(0)))throw new IOException("Duplicate field ID");
            String flag=row.get(activeColumn);
            if(!flag.equals("true")&&!flag.equals("false"))
                throw new IOException("Invalid field active flag");
            if(flag.equals("true")){slots.add(i);active.add(row);}
        }
        int old=-1;
        for(int i=0;i<active.size();i++)
            if(active.get(i).get(0).equals(fieldId)){old=i;break;}
        if(old<0)throw new IOException("Active field not found");
        if(newIndex<0||newIndex>=active.size())
            throw new IOException("Field destination is out of range");
        if(old==newIndex)return false;
        List<String> changed=active.remove(old);
        active.add(newIndex,changed);
        for(int i=0;i<slots.size();i++)rows.set(slots.get(i),active.get(i));
        return true;
    }
}
