package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public final class FieldOrderingSmoke {
    private static List<String> row(String id,String value,String active){
        return new ArrayList<>(Arrays.asList(id,"Label","Checkbox","false",value,active));
    }
    private static void check(boolean value,String message){
        if(!value)throw new AssertionError(message);
    }
    private static void rejects(List<List<String>> data,String id,int index)throws Exception{
        String previous=CsvCodec.write(data);
        try{FieldOrdering.moveActive(data,id,index,5);throw new AssertionError("Accepted invalid move");}
        catch(IOException expected){}
        check(previous.equals(CsvCodec.write(data)),"Invalid reorder mutated data");
    }
    public static void main(String[] args)throws Exception{
        List<List<String>> data=new ArrayList<>();
        data.add(new ArrayList<>(Arrays.asList("ID","Label","Kind","Required","Value","Active")));
        data.add(row("a","true","true"));
        data.add(row("archived","OLD","false"));
        data.add(row("b","false","true"));
        data.add(row("c","true","true"));
        check(FieldOrdering.moveActive(data,"c",0,5),"move did not change order");
        check(data.get(1).get(0).equals("c"),"move to front failed");
        check(data.get(2).get(0).equals("archived"),"archived slot moved");
        check(data.get(3).get(0).equals("a"),"other active order wrong");
        check(data.get(4).get(0).equals("b"),"other active order wrong");
        check(data.get(1).get(4).equals("true"),"moved value lost");
        check(!FieldOrdering.moveActive(data,"c",0,5),"same-position move should be no-op");
        rejects(data,"archived",0);
        rejects(data,"not-there",0);
        rejects(data,"c",-1);
        rejects(data,"c",3);
        System.out.println("FieldOrderingSmoke PASS");
    }
}
