package com.accubook.crm;

import android.util.AtomicFile;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Optional local repeat-service reminders: month/mileage rules, no automatic
 * contact, notifications, schedule creation or external APIs.
 * A service completion/reset is explicitly confirmed by the owner.
 */
public final class RecurringServices {
    public static final String[] HEADER={
        "ScheduleID","CustomerID","SourceJobID","ServiceLabel","SiteName",
        "LastServiceDate","IntervalMonths","LastMileage","IntervalMiles",
        "DueDate","DueMileage","Active"
    };
    public static final class Rule {
        public final String id,customerId,jobId,label,site,lastDate,lastMiles,
            months,miles,dueDate,dueMiles;
        public final boolean active;
        Rule(List<String> values){
            id=values.get(0);customerId=values.get(1);jobId=values.get(2);
            label=values.get(3);site=values.get(4);lastDate=values.get(5);
            months=values.get(6);lastMiles=values.get(7);miles=values.get(8);
            dueDate=values.get(9);dueMiles=values.get(10);
            active=Boolean.parseBoolean(values.get(11));
        }
        public boolean dueToday(){
            return active&&ServiceIntervals.dueByDate(dueDate,LocalDate.now().toString());
        }
    }
    private final WorkspaceStore store;
    private final File file;
    public RecurringServices(WorkspaceStore store){
        this.store=store;
        this.file=new File(store.root(),"master_data/service_intervals.csv");
    }
    private static List<String> row(String... parts){
        return new ArrayList<>(Arrays.asList(parts));
    }
    private static List<List<String>> blank(){
        List<List<String>> rows=new ArrayList<>();
        rows.add(row(HEADER));return rows;
    }
    private static String value(String input,int limit,boolean required){
        String v=input==null?"":input.trim();
        if(v.length()>limit||(required&&v.isEmpty()))
            throw new IllegalArgumentException("Required or oversized service field");
        for(int i=0;i<v.length();i++)if(Character.isISOControl(v.charAt(i)))
            throw new IllegalArgumentException("Invalid service field");
        return v;
    }
    private static int months(String input){
        try{
            int n=Integer.parseInt(input.trim());
            if(n<0||n>120)throw new IllegalArgumentException("Choose 0–120 months");
            return n;
        }catch(NumberFormatException|NullPointerException ex){
            throw new IllegalArgumentException("Enter whole-number months",ex);
        }
    }
    private static String miles(String input){
        String v=value(input,9,false);
        if(v.isEmpty())return "0";
        try{
            long n=Long.parseLong(v);
            if(n<0||n>1000000)throw new IllegalArgumentException("Mileage interval too large");
            return Long.toString(n);
        }catch(NumberFormatException ex){
            throw new IllegalArgumentException("Enter a whole-number mileage interval",ex);
        }
    }
    private static void write(File file,List<List<String>> rows)throws IOException{
        byte[] data=CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8);
        if(data.length>4*1024*1024)throw new IOException("Recurring service data too large");
        AtomicFile atomic=new AtomicFile(file);FileOutputStream out=null;
        try{
            out=atomic.startWrite();out.write(data);atomic.finishWrite(out);
        }catch(IOException|RuntimeException ex){
            if(out!=null)atomic.failWrite(out);
            throw ex;
        }
    }
    private List<List<String>> read()throws IOException{
        if(!file.isFile()&&!new File(file.getPath()+".bak").isFile())write(file,blank());
        ByteArrayOutputStream result=new ByteArrayOutputStream();
        try(InputStream in=new AtomicFile(file).openRead()){
            byte[] block=new byte[8192];int n;
            while((n=in.read(block))!=-1){
                if(result.size()+n>4*1024*1024)
                    throw new IOException("Recurring service CSV is oversized");
                result.write(block,0,n);
            }
        }
        List<List<String>> rows=CsvCodec.read(result.toString("UTF-8"));
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(HEADER))||rows.size()>2001)
            throw new IOException("Unknown service schedule version or too many entries");
        Set<String> ids=new HashSet<>();
        for(int i=1;i<rows.size();i++){
            List<String> r=rows.get(i);
            if(r.size()!=HEADER.length||!r.get(0).matches("SERVICE-[a-f0-9]{32}")||
                !ids.add(r.get(0))||r.get(3).isEmpty()||
                !Arrays.asList("true","false").contains(r.get(11)))
                throw new IOException("Invalid recurring service row");
            try{
                if(!r.get(7).isEmpty()){
                    long current=Long.parseLong(r.get(7));
                    if(current<0||current>9999999)throw new IOException(
                        "Out-of-range recorded mileage");
                }
                int month=months(r.get(6));
                String nextDate=ServiceIntervals.dueDate(r.get(5),month);
                String nextMiles=ServiceIntervals.dueMileage(r.get(7),r.get(8));
                if(month==0&&nextMiles.isEmpty()||
                    !r.get(9).equals(nextDate)||!r.get(10).equals(nextMiles))
                    throw new IOException("Recurring schedule has inconsistent due values");
            }catch(IllegalArgumentException ex){
                throw new IOException("Invalid recurring service interval",ex);
            }
        }
        return rows;
    }
    public synchronized List<Rule> all()throws IOException{
        List<Rule> result=new ArrayList<>();
        List<List<String>> rows=read();
        for(List<String> r:rows.subList(1,rows.size()))result.add(new Rule(r));
        return result;
    }
    public synchronized Rule save(WorkspaceStore.Job source,String existingId,
            String title,String site,String finished,String intervalMonths,
            String lastMileage,String intervalMiles)throws IOException{
        boolean known=false;
        for(WorkspaceStore.Job job:store.jobs())
            if(job.id.equals(source.id)&&job.customerId.equals(source.customerId))
                known=true;
        if(!known)throw new IOException("Unknown source job");
        String label=value(title,180,true),location=value(site,180,false);
        int m=months(intervalMonths);
        String mileageInterval=miles(intervalMiles);
        String currentMileage=value(lastMileage,9,false);
        if(!currentMileage.isEmpty()){
            try{
                long reading=Long.parseLong(currentMileage);
                if(reading<0||reading>9999999)throw new IllegalArgumentException(
                    "Mileage reading is out of range");
            }catch(NumberFormatException ex){
                throw new IllegalArgumentException("Enter whole-number mileage",ex);
            }
        }
        if(!mileageInterval.equals("0")&&currentMileage.isEmpty())
            throw new IllegalArgumentException("Enter last mileage for mileage reminders");
        if(m==0 && mileageInterval.equals("0"))
            throw new IllegalArgumentException("Set months, miles, or both");
        String completed=value(finished,10,true);
        String nextDate=ServiceIntervals.dueDate(completed,m);
        String nextMileage=ServiceIntervals.dueMileage(currentMileage,mileageInterval);
        String id=existingId==null?"SERVICE-"+UUID.randomUUID().toString().replace("-",""):
            value(existingId,40,true);
        if(!id.matches("SERVICE-[a-f0-9]{32}"))throw new IOException("Invalid schedule ID");
        List<List<String>> rows=read();
        List<String> record=row(id,source.customerId,source.id,label,location,
            completed,Integer.toString(m),currentMileage,mileageInterval,
            nextDate,nextMileage,"true");
        int index=-1;
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id))index=i;
        if(existingId!=null){
            if(index<0)throw new IOException("Recurring service not found");
            if(!rows.get(index).get(2).equals(source.id))
                throw new IOException("Cannot move recurrence to another source job");
        }
        if(index<0)rows.add(record);else rows.set(index,record);
        write(file,rows);
        return new Rule(record);
    }
    public synchronized void setActive(String id,boolean enabled)throws IOException{
        List<List<String>> rows=read();boolean found=false;
        for(int i=1;i<rows.size();i++)
            if(rows.get(i).get(0).equals(id)){
                rows.get(i).set(11,Boolean.toString(enabled));
                found=true;break;
            }
        if(!found)throw new IOException("Service schedule not found");
        write(file,rows);
    }
}
