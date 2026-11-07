package com.accubook.crm;

/** Free text never requires a drop-down match. */
public final class CatalogSuggestionsSmoke {
    private static void check(boolean ok){if(!ok)throw new AssertionError("Scoring invariant");}
    public static void main(String[] args){
        check(CatalogSuggestions.score("fence post","Fence post","Carpentry")>=400);
        check(CatalogSuggestions.score("installed fence post", "Fence post","Carpentry")>0);
        check(CatalogSuggestions.score("oil change","Roof cap","Roofing")==0);
        check(CatalogSuggestions.score("","Fence post","Carpentry")==0);
        System.out.println("CatalogSuggestionsSmoke: PASS");
    }
}