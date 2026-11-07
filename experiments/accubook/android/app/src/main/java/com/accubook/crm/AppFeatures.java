package com.accubook.crm;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * Presentation feature switches, NOT destructive migrations. Disabled modules retain
 * their original local records and can be re-enabled without any data loss.
 * Android's TalkBack is controlled in Android Accessibility settings; this app
 * never attempts to enable or disable a system accessibility service.
 */
public final class AppFeatures {
    public static final String CREWS="crews";
    public static final String ADVANCED_SCHEDULING="advanced_scheduling";
    public static final String PRICEBOOK="pricebook";
    public static final String MATERIALS="materials";
    public static final String MULTI_PROPERTY="multi_property";
    public static final String RECURRING="recurring";
    public static final String WORKER_TIME="worker_time";
    public static final String GPS_ROUTES="gps_routes";
    public static final String EXTRA_MOVE_CONTROLS="extra_move_controls";
    public static final String[] KEYS={
        CREWS, ADVANCED_SCHEDULING, PRICEBOOK, MATERIALS, MULTI_PROPERTY,
        RECURRING, WORKER_TIME, GPS_ROUTES, EXTRA_MOVE_CONTROLS
    };
    public static final String[] LABELS={
        "Crew assignment", "Advanced scheduling", "Services and pricebook",
        "Materials and deliveries", "Multiple properties (preview)",
        "Recurring jobs (preview)", "Worker time tracking",
        "Private GPS route recording", "Show extra reorder buttons"
    };

    private final SharedPreferences preferences;
    public AppFeatures(Context context){
        preferences=context.getSharedPreferences("accubook.features.v1",Context.MODE_PRIVATE);
    }
    public boolean enabled(String key){
        boolean known=false;
        for(String candidate:KEYS)if(candidate.equals(key))known=true;
        if(!known)throw new IllegalArgumentException("Unknown feature switch");
        return preferences.getBoolean(key, MATERIALS.equals(key));
    }
    public void set(String key,boolean enabled){
        this.enabled(key); // validate
        if(!preferences.edit().putBoolean(key,enabled).commit())
            throw new IllegalStateException("Could not save local feature setting");
    }
}
