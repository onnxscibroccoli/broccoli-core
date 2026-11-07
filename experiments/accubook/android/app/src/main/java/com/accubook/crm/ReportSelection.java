package com.accubook.crm;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * Immutable, explicit export allow-list. Every category is opt-in, including
 * Cash App, cash logs and all other payment methods. No implicit "all".
 */
public final class ReportSelection {
    private final boolean[] sections;
    private final Set<String> methods;
    private final Set<String> categories;
    public static final String[] PAYMENT_METHODS = {
        "Cash", "Check", "Cash App", "PayPal", "Bank Transfer", "Other"
    };
    public static final int SECTION_COUNT=6;

    public ReportSelection(boolean[] chosen,Set<String> paymentMethods,
                           Set<String> expenseCategories){
        if(chosen==null||chosen.length!=SECTION_COUNT)
            throw new IllegalArgumentException("Report selection is incomplete");
        sections=chosen.clone();
        boolean any=false;
        for(boolean enabled:sections)any|=enabled;
        if(!any)throw new IllegalArgumentException("Choose a report section");
        if(paymentMethods==null||expenseCategories==null)
            throw new IllegalArgumentException("Export filters are missing");
        methods=Collections.unmodifiableSet(new LinkedHashSet<>(paymentMethods));
        categories=Collections.unmodifiableSet(new LinkedHashSet<>(expenseCategories));
        if(!Arrays.asList(PAYMENT_METHODS).containsAll(methods))
            throw new IllegalArgumentException("Unknown payment method");
        if(categories.contains(null)||categories.contains(""))
            throw new IllegalArgumentException("Invalid expense category");
        if(sections[3]&&methods.isEmpty())
            throw new IllegalArgumentException("Choose payment methods, or turn off payments");
        if(sections[4]&&categories.isEmpty())
            throw new IllegalArgumentException("Choose expense categories, or turn off expenses");
    }
    public boolean include(int section){
        if(section<0||section>=sections.length)throw new IllegalArgumentException("Unknown section");
        return sections[section];
    }
    public boolean[] sections(){return sections.clone();}
    public Set<String> methods(){return methods;}
    public Set<String> categories(){return categories;}
    public boolean payment(String method){return sections[3]&&methods.contains(method);}
    public boolean expense(String category){return sections[4]&&categories.contains(category);}
}
