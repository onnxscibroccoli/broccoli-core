package com.accubook.crm;

/** Due-date/mileage calculations never depend on network or scheduled workers. */
public final class ServiceIntervalsSmoke {
    private static void check(boolean ok,String message){
        if(!ok)throw new AssertionError(message);
    }
    public static void main(String[] args){
        check(ServiceIntervals.dueDate("2026-01-31",1).equals("2026-02-28"),
            "Month-end rollover wrong");
        check(ServiceIntervals.dueDate("2024-02-29",12).equals("2025-02-28"),
            "Leap-year anniversary wrong");
        check(ServiceIntervals.dueDate("2026-03-01",6).equals("2026-09-01"),
            "Semiannual due date wrong");
        check(ServiceIntervals.dueDate("2026-03-01",0).isEmpty(),
            "Mileage-only service should have no date");
        check(ServiceIntervals.dueMileage("55812","3000").equals("58812"),
            "Oil-change odometer interval wrong");
        check(ServiceIntervals.dueMileage("","0").isEmpty(),
            "Date-only service created false mileage threshold");
        check(ServiceIntervals.dueByDate("2026-11-07","2026-11-07"),
            "Due-today service missing");
        check(!ServiceIntervals.dueByDate("","2026-11-07"),
            "Mileage-only service incorrectly due by date");
        check(!ServiceIntervals.dueByDate("2026-11-08","2026-11-07"),
            "Future reminder incorrectly overdue");
        boolean rejected=false;
        try{ServiceIntervals.dueMileage("no reading","3000");}
        catch(IllegalArgumentException expected){rejected=true;}
        check(rejected,"Invalid odometer accepted");
        System.out.println("ServiceIntervalsSmoke: PASS");
    }
}