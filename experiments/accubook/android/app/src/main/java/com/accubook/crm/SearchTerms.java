package com.accubook.crm;

import java.text.Normalizer;
import java.util.Locale;

/** Pure-Java offline matching. All query words can match different record fields. */
public final class SearchTerms {
    private SearchTerms(){}
    public static String normalize(String value){
        if(value==null)return "";
        return Normalizer.normalize(value,Normalizer.Form.NFKD)
            .replaceAll("\\p{M}+","")
            .toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+"," ").trim();
    }
    public static boolean matches(String query,String... values){
        String q=normalize(query);
        if(q.length()<2)return false;
        StringBuilder target=new StringBuilder();
        for(String value:values)target.append(" ").append(normalize(value));
        String haystack=target.toString();
        for(String token:q.split(" ")){
            if(!haystack.contains(token))return false;
        }
        return true;
    }
    public static int score(String query,String title,String... other){
        if(!matches(query,join(title,other)))return 0;
        String q=normalize(query),t=normalize(title);
        if(t.equals(q))return 100;
        if(t.startsWith(q))return 80;
        if(t.contains(q))return 65;
        return 20;
    }
    private static String join(String title,String[] more){
        StringBuilder result=new StringBuilder(title==null?"":title);
        for(String v:more)result.append(' ').append(v);
        return result.toString();
    }
}
