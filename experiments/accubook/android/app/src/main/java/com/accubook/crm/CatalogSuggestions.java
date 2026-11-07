package com.accubook.crm;

import java.util.Locale;

/** Lightweight, entirely local free-text matcher; suggestions never force an item. */
public final class CatalogSuggestions {
    private CatalogSuggestions(){}
    public static int score(String query,String name,String category) {
        String q=normal(query),n=normal(name),c=normal(category);
        if(q.isEmpty())return 0;
        if(n.equals(q))return 1000;
        if(n.contains(q))return 400;
        int score=0;
        for(String token:q.split(" ")) {
            if(token.length()<3 || token.equals("the")||token.equals("for")||
                token.equals("and")||token.equals("with")||token.equals("new")||
                token.equals("job")||token.equals("work"))continue;
            if(n.contains(token))score+=25;
            else if(c.contains(token))score+=5;
        }
        return score;
    }
    private static String normal(String text){
        return text==null?"":text.toLowerCase(Locale.ROOT)
            .replaceAll("[^a-z0-9]+"," ").trim();
    }
}
