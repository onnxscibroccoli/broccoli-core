package com.accubook.crm;

/** Search is deterministic, accent-insensitive and works without services. */
public final class SearchTermsSmoke {
    private static void require(boolean ok,String message){
        if(!ok)throw new AssertionError(message);
    }
    public static void main(String[] args){
        require(SearchTerms.matches("jose","José González"),"Accent normalization failed");
        require(SearchTerms.matches("john 02190","John Smith","South Weymouth MA 02190"),
            "Cross-column lookup failed");
        require(SearchTerms.matches("781 555","(781) 555-0134"),
            "Phone punctuation lookup failed");
        require(SearchTerms.matches("vin 123","Vehicle VIN","123-456"),
            "Vehicle custom-field query failed");
        require(SearchTerms.matches("INV-ABCD","INV-ABCD-EFGH-1234"),
            "Invoice prefix query failed");
        require(!SearchTerms.matches("john missing","John Smith","02190"),
            "Multiword query returned incomplete match");
        require(!SearchTerms.matches("","John Smith"),"Blank search returned all records");
        require(!SearchTerms.matches("x","John Smith"),"One-character broad search allowed");
        require(SearchTerms.score("jose","José González") >
                SearchTerms.score("jose","Repair job","José González"),
            "Title match should outrank nested-field match");
        System.out.println("SearchTermsSmoke: PASS");
    }
}
