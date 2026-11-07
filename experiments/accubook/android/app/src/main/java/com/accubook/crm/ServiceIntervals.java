package com.accubook.crm;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;

/** Exact, timezone-independent service interval arithmetic. No background scheduling. */
public final class ServiceIntervals {
    private ServiceIntervals(){}
    public static String dueDate(String completedIso,int everyMonths){
        if(everyMonths<0||everyMonths>120)
            throw new IllegalArgumentException("Months must be from 0 to 120");
        final LocalDate completed;
        try{completed=LocalDate.parse(completedIso);}
        catch(NullPointerException|DateTimeParseException error){
            throw new IllegalArgumentException("Choose a valid date",error);
        }
        return everyMonths==0?"":completed.plusMonths(everyMonths).toString();
    }
    public static String dueMileage(String atMiles,String everyMiles){
        if(everyMiles==null||everyMiles.trim().isEmpty()||"0".equals(everyMiles.trim()))
            return "";
        try{
            long interval=Long.parseLong(everyMiles.trim());
            long last=Long.parseLong(atMiles.trim());
            if(interval<1||interval>1000000||last<0||last>9999999||
                last+interval>9999999)
                throw new IllegalArgumentException("Mileage outside supported range");
            return Long.toString(last+interval);
        }catch(NumberFormatException|NullPointerException error){
            throw new IllegalArgumentException(
                "Enter whole-number last mileage and positive mileage interval",error);
        }
    }
    public static boolean dueByDate(String iso,String todayIso){
        if(iso==null||iso.isEmpty())return false;
        return !LocalDate.parse(iso).isAfter(LocalDate.parse(todayIso));
    }
}
