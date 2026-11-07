package com.accubook.crm;

import java.io.IOException;

/** Pure-JVM contract tests for onboarding and restore, no Android runtime. */
public final class BusinessSetupProfileSmoke {
    private static void check(boolean ok,String message){
        if(!ok)throw new AssertionError(message);
    }
    private static void invalid(String csv,String reason) throws Exception{
        boolean rejected=false;
        try{BusinessSetupProfile.fromCsv(csv);}
        catch(IOException expected){rejected=true;}
        check(rejected,reason);
    }
    public static void main(String[] args) throws Exception {
        BusinessSetupProfile initial=BusinessSetupProfile.defaults();
        check(initial.team.equals("SOLO"),"First-run must be solo");
        check(initial.catalog && !initial.crew && !initial.gps
            && !initial.advancedCalendar && !initial.recurring,
            "Unsafe/default modules were enabled");
        check(initial.status.equals(BusinessSetupProfile.NOT_STARTED),
            "An unanswered questionnaire was marked complete");
        BusinessSetupProfile p=new BusinessSetupProfile(BusinessSetupProfile.COMPLETE,
            "TEAM","roofing","SRS, QXO \"North\"",true,true,
            true,true,true,false,false,true);
        String csv=p.toCsv();
        BusinessSetupProfile restored=BusinessSetupProfile.fromCsv(csv);
        check(restored.status.equals("COMPLETE")&&restored.crew
            &&restored.materialDeliveries&&restored.dumpsters&&restored.recurring,
            "Selections did not survive CSV roundtrip");
        check(restored.vendors.equals("SRS, QXO \"North\""),
            "Quoted supplier names failed CSV roundtrip");
        BusinessSetupProfile later=restored.withFeature("gps",true);
        check(later.gps&&!restored.gps&&later.vendors.equals(restored.vendors),
            "Changing one switch modified unrelated answers");
        check(!restored.enabled("gps")&&restored.enabled("recurring_services"),
            "Incorrect key mapping");
        invalid(csv.replace("TEAM","EITHER"),"Invalid team accepted");
        invalid(csv.replace("COMPLETE","DELETED"),"Unknown status accepted");
        invalid(csv.replace(",false,false,true\r\n",",FALSE,false,true\r\n"),
            "Noncanonical boolean accepted");
        invalid(csv.replace("Version","Schema"),"Unknown schema accepted");
        invalid(csv+"extra,row\r\n","Extra data row accepted");
        boolean huge=false;
        try{new BusinessSetupProfile("COMPLETE","SOLO",
            "x".repeat(121),"",false,false,false,true,false,false,false,false);}
        catch(IllegalArgumentException expected){huge=true;}
        check(huge,"Unbounded text accepted");
        boolean unknown=false;
        try{restored.withFeature("remote_owner_unlock",true);}
        catch(IllegalArgumentException expected){unknown=true;}
        check(unknown,"Unknown module accepted");
        System.out.println("BusinessSetupProfileSmoke: PASS");
    }
}
