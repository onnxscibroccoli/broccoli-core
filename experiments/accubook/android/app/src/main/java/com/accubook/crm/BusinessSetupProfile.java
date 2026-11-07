package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Portable, human-editable onboarding profile. Versioned CSV is the source of
 * truth for module visibility AFTER setup; old installations retain their
 * existing preferences until the owner runs setup.
 *
 * No vendor accounts, location permission, network service or LLM is used.
 */
public final class BusinessSetupProfile {
    public static final String NOT_STARTED="NOT_STARTED", COMPLETE="COMPLETE", SKIPPED="SKIPPED";
    public static final String SOLO="SOLO", TEAM="TEAM";
    private static final List<String> HEADER=Arrays.asList(
        "Version","Status","Team","Trade","Vendors","MaterialDeliveries","Dumpsters",
        "Crew","Catalog","WorkerTime","GPS","AdvancedCalendar","Recurring");

    public final String status,team,trade,vendors;
    public final boolean materialDeliveries,dumpsters,crew,catalog,workerTime,gps,advancedCalendar,recurring;

    public BusinessSetupProfile(String status,String team,String trade,String vendors,
          boolean materialDeliveries,boolean dumpsters,boolean crew,boolean catalog,
          boolean workerTime,boolean gps,boolean advancedCalendar,boolean recurring) {
        if (!Arrays.asList(NOT_STARTED,COMPLETE,SKIPPED).contains(status))
            throw new IllegalArgumentException("Unknown setup state");
        if (!Arrays.asList(SOLO,TEAM).contains(team))
            throw new IllegalArgumentException("Choose solo or crew operation");
        this.status=status;
        this.team=team;
        this.trade=checked(trade,120);
        this.vendors=checked(vendors,500);
        this.materialDeliveries=materialDeliveries;
        this.dumpsters=dumpsters;
        this.crew=crew;
        this.catalog=catalog;
        this.workerTime=workerTime;
        this.gps=gps;
        this.advancedCalendar=advancedCalendar;
        this.recurring=recurring;
    }
    private static String checked(String value,int max) {
        String trimmed=value==null?"":value.trim();
        if (trimmed.length()>max || trimmed.indexOf('\0')>=0 ||
            trimmed.indexOf('\n')>=0 || trimmed.indexOf('\r')>=0)
            throw new IllegalArgumentException("Setup text must be a single short line");
        return trimmed;
    }
    public static BusinessSetupProfile defaults() {
        return new BusinessSetupProfile(NOT_STARTED,SOLO,"","",false,false,
            false,true,false,false,false,false);
    }
    /** Requested modules are independent; do not enable GPS/calendar implicitly. */
    public boolean enabled(String key) {
        switch(key){
            case "crew": return crew;
            case "catalog": return catalog;
            case "worker_time": return workerTime;
            case "gps": return gps;
            case "advanced_calendar": return advancedCalendar;
            case "recurring_services": return recurring;
            default: throw new IllegalArgumentException("Unknown module key");
        }
    }
    /** Preserve all other questionnaire answers when Settings changes one switch. */
    public BusinessSetupProfile withFeature(String key,boolean value){
        // enabled() validates the key before changing anything.
        enabled(key);
        return new BusinessSetupProfile(status,team,trade,vendors,materialDeliveries,dumpsters,
            key.equals("crew")?value:crew,key.equals("catalog")?value:catalog,
            key.equals("worker_time")?value:workerTime,key.equals("gps")?value:gps,
            key.equals("advanced_calendar")?value:advancedCalendar,
            key.equals("recurring_services")?value:recurring);
    }
    public String toCsv(){
        List<List<String>> rows=new ArrayList<>();
        rows.add(HEADER);
        rows.add(Arrays.asList("1",status,team,trade,vendors,
            Boolean.toString(materialDeliveries),Boolean.toString(dumpsters),
            Boolean.toString(crew),Boolean.toString(catalog),
            Boolean.toString(workerTime),Boolean.toString(gps),
            Boolean.toString(advancedCalendar),Boolean.toString(recurring)));
        return CsvCodec.write(rows);
    }
    public static BusinessSetupProfile fromCsv(String csv) throws IOException {
        List<List<String>> rows=CsvCodec.read(csv);
        if(rows.size()!=2||!HEADER.equals(rows.get(0))||
            rows.get(1).size()!=HEADER.size()||!"1".equals(rows.get(1).get(0)))
            throw new IOException("Unexpected business setup schema/version");
        List<String> row=rows.get(1);
        try{
            for(int i=5;i<=12;i++)
                if(!row.get(i).equals("true")&&!row.get(i).equals("false"))
                    throw new IllegalArgumentException("Invalid module preference");
            return new BusinessSetupProfile(row.get(1),row.get(2),row.get(3),row.get(4),
                Boolean.parseBoolean(row.get(5)),Boolean.parseBoolean(row.get(6)),
                Boolean.parseBoolean(row.get(7)),Boolean.parseBoolean(row.get(8)),
                Boolean.parseBoolean(row.get(9)),Boolean.parseBoolean(row.get(10)),
                Boolean.parseBoolean(row.get(11)),Boolean.parseBoolean(row.get(12)));
        }catch(IllegalArgumentException error){
            throw new IOException("Invalid business setup values",error);
        }
    }
}
