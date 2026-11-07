package com.accubook.crm;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

/** Explicit, immutable export allow-list. Nothing is exported by implicit default. */
public final class ExportSelection {
    public static final int SECTION_COUNT=6;
    private final boolean[] sections;
    public final Set<String> paymentMethods;
    public final Set<String> expenseCategories;
    public ExportSelection(boolean[] sections,Set<String> paymentMethods,
                           Set<String> expenseCategories){
        if(sections==null || sections.length!=SECTION_COUNT)
            throw new IllegalArgumentException("Invalid section selection");
        this.sections=sections.clone();
        boolean any=false; for(boolean selected:sections)any|=selected;
        if(!any)throw new IllegalArgumentException("Select a report category");
        this.paymentMethods=immutable(paymentMethods);
        this.expenseCategories=immutable(expenseCategories);
        if(sections[3]&&this.paymentMethods.isEmpty())
            throw new IllegalArgumentException("Select payment methods or disable payments");
        if(sections[4]&&this.expenseCategories.isEmpty())
            throw new IllegalArgumentException("Select expense categories or disable expenses");
    }
    private static Set<String> immutable(Set<String> values){
        if(values==null)throw new IllegalArgumentException("Explicit filters required");
        LinkedHashSet<String> copy=new LinkedHashSet<>();
        for(String s:values){
            if(s==null||s.trim().isEmpty()||s.length()>128)
                throw new IllegalArgumentException("Invalid export filter");
            copy.add(s);
        }
        return Collections.unmodifiableSet(copy);
    }
    public boolean included(int section){return sections[section];}
    public boolean[] selectedSections(){return sections.clone();}
    public boolean includesPayment(String method){
        return sections[3]&&paymentMethods.contains(method);
    }
    public boolean includesExpense(String category){
        return sections[4]&&expenseCategories.contains(category);
    }

}
