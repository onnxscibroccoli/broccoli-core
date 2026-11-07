package com.accubook.crm;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class PhotoOrderingSmoke {
    private static String photo(char c){return "PHOTO-"+String.valueOf(c).repeat(32)+".jpg";}
    private static void check(boolean ok,String message){
        if(!ok)throw new AssertionError(message);
    }
    private static void rejects(List<String> actual,List<String> saved){
        try{PhotoOrdering.merge(actual,saved);throw new AssertionError("Invalid index accepted");}
        catch(IOException expected){}
    }
    public static void main(String[] args)throws Exception {
        String a=photo('a'),b=photo('b'),c=photo('c');
        List<String> order=PhotoOrdering.merge(Arrays.asList(c,a,b),Arrays.asList(b,a));
        check(order.equals(Arrays.asList(b,a,c)),"new photo did not append");
        List<String> changed=PhotoOrdering.move(order,c,0);
        check(changed.equals(Arrays.asList(c,b,a)),"reorder incorrect");
        check(order.equals(Arrays.asList(b,a,c)),"reorder mutated caller list");
        rejects(Arrays.asList(a,b),Arrays.asList(a,a));
        rejects(Collections.singletonList(a),Collections.singletonList(b));
        rejects(Arrays.asList(a,"../../escape"),Collections.emptyList());
        try{PhotoOrdering.move(order,a,3);throw new AssertionError("Out of range accepted");}
        catch(IOException expected){}
        System.out.println("PhotoOrderingSmoke PASS");
    }
}
