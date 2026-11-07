package com.accubook.crm;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.Arrays;

/**
 * Presentation-only feature switches. Disabling a feature hides related UI
 * without deleting CSV data, changing backups, or asking for permissions.
 */
public final class FeatureSettings {
    private static final String PREFS="accubook_features_v1";
    public static final String CREW="crew";
    public static final String CATALOG="catalog";
    public static final String WORKER_TIME="worker_time";
    public static final String GPS="gps";
    public static final String ADVANCED_CALENDAR="advanced_calendar";
    public static final String RECURRING="recurring_services";
    public static final String[] KEYS={
        CREW,CATALOG,WORKER_TIME,GPS,ADVANCED_CALENDAR,RECURRING
    };
    public static final String[] LABELS={
        "Crew assignment fields",
        "Services and materials pricebook",
        "Worker time tracking",
        "Private GPS route capture",
        "Experimental calendar account sync",
        "Repeat-service due dates (monthly or mileage)"
    };
    private FeatureSettings(){}
    private static void validate(String key){
        if(!Arrays.asList(KEYS).contains(key))
            throw new IllegalArgumentException("Unknown Accubook feature");
    }
    public static boolean defaultEnabled(String key){
        validate(key);
        return CATALOG.equals(key); // Preserve existing visible pricebook.
    }
    public static boolean enabled(Context context,String key){
        validate(key);
        return context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
            .getBoolean(key,defaultEnabled(key));
    }
    public static void set(Context context,String key,boolean enabled){
        validate(key);
        SharedPreferences p=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
        if(!p.edit().putBoolean(key,enabled).commit())
            throw new IllegalStateException("Feature setting could not be saved");
    }
}
