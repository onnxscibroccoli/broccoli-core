package com.accubook.crm;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

/**
 * Portable v1 schema and numeric rules for OPTIONAL, owner-maintained inventory.
 * These are records of observed stock and movements, not an automatic stock ledger.
 * Pure Java so the same rules run in restore validation and standalone CI.
 */
public final class InventoryRules {
    public static final String[] COMPANY = {
        "MaterialID","Name","Unit","OnHand","UnitCost","PricebookID"
    };
    public static final String[] SITE = {
        "EntryID","Name","Unit","Quantity","Status"
    };
    public static final String[] TOOLS = {
        "ToolID","Name","AssetTag","Status","JobID"
    };
    public static final List<String> SITE_STATES =
        Arrays.asList("Delivered","Used","Returned");
    public static final List<String> TOOL_STATES =
        Arrays.asList("Available","Checked Out","Maintenance");

    private InventoryRules() {}

    public static String text(String value,int max,boolean required) {
        String clean=value==null?"":value.trim();
        if(clean.length()>max || (required&&clean.isEmpty()))
            throw new IllegalArgumentException("Enter a value up to "+max+" characters");
        for(int i=0;i<clean.length();i++)
            if(Character.isISOControl(clean.charAt(i)))
                throw new IllegalArgumentException("Inventory text contains a control character");
        return clean;
    }

    public static String quantity(String raw,boolean zeroAllowed) {
        try {
            BigDecimal v=new BigDecimal(raw.trim());
            if(v.scale()>4 || v.signum()<(zeroAllowed?0:1) ||
                v.compareTo(new BigDecimal("1000000"))>0)
                throw new IllegalArgumentException("Quantity must be positive (max 1,000,000; 4 decimals)");
            return v.stripTrailingZeros().toPlainString();
        } catch(NumberFormatException|NullPointerException error) {
            throw new IllegalArgumentException("Enter a numeric quantity",error);
        }
    }

    public static String cost(String raw) {
        try {
            BigDecimal v=new BigDecimal(raw.trim());
            if(v.scale()>2 || v.signum()<0 || v.compareTo(new BigDecimal("1000000"))>0)
                throw new IllegalArgumentException("Cost must be 0–1,000,000 with 2 decimals");
            return v.setScale(2).toPlainString();
        } catch(NumberFormatException|NullPointerException error) {
            throw new IllegalArgumentException("Enter a numeric unit cost",error);
        }
    }

    private static void validId(String id,String prefix) {
        if(id==null||!id.matches(prefix+"-[a-f0-9]{32}"))
            throw new IllegalArgumentException("Invalid inventory ID");
    }
    private static void size(List<String> row,int required) {
        if(row==null||row.size()!=required)
            throw new IllegalArgumentException("Unexpected inventory CSV columns");
    }
    private static void canonical(String actual,String expected) {
        if(!actual.equals(expected))
            throw new IllegalArgumentException("Inventory number is not normalized");
    }

    public static void company(List<String> row) {
        size(row,COMPANY.length);
        validId(row.get(0),"MAT");
        text(row.get(1),160,true);
        text(row.get(2),40,true);
        canonical(row.get(3),quantity(row.get(3),true));
        canonical(row.get(4),cost(row.get(4)));
        if(!row.get(5).isEmpty())validId(row.get(5),"CAT");
    }

    public static void site(List<String> row) {
        size(row,SITE.length);
        validId(row.get(0),"SITE");
        text(row.get(1),160,true);
        text(row.get(2),40,true);
        canonical(row.get(3),quantity(row.get(3),false));
        if(!SITE_STATES.contains(row.get(4)))
            throw new IllegalArgumentException("Unknown site material status");
    }

    public static void tool(List<String> row) {
        size(row,TOOLS.length);
        validId(row.get(0),"TOOL");
        text(row.get(1),160,true);
        text(row.get(2),100,false);
        if(!TOOL_STATES.contains(row.get(3)))
            throw new IllegalArgumentException("Unknown tool status");
        if("Checked Out".equals(row.get(3)))validId(row.get(4),"JOB");
        else if(!row.get(4).isEmpty())
            throw new IllegalArgumentException("Non-checked-out tool retains a job");
    }
}
