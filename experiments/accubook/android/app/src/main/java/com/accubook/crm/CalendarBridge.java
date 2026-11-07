package com.accubook.crm;

import android.Manifest;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.CalendarContract;
import android.util.AtomicFile;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Device calendar provider integration: explicit opt-in and a selected account.
 * Google Calendar sync, if any, is performed by the user's installed calendar
 * account's sync adapter; Accubook has no network or OAuth credentials.
 */
public final class CalendarBridge {
    public static final class CalendarChoice {
        public final long id;
        public final String label,account;
        CalendarChoice(long id,String label,String account){
            this.id=id;this.label=label;this.account=account;
        }
        @Override public String toString(){return label+" · "+account;}
    }
    private static final String[] LINKS={"JobID","CalendarID","EventID"};
    private final Context context;
    private final WorkspaceStore store;
    private final CrmWorkspace crm;
    public CalendarBridge(Context context,WorkspaceStore store) {
        this.context=context;this.store=store;this.crm=new CrmWorkspace(store);
    }
    public static boolean enabled(Context ctx){
        return ctx.getSharedPreferences("accubook.calendar",Context.MODE_PRIVATE)
            .getBoolean("enabled",false);
    }
    public static long selectedCalendar(Context ctx){
        return ctx.getSharedPreferences("accubook.calendar",Context.MODE_PRIVATE)
            .getLong("calendar",-1);
    }
    public static void setEnabled(Context context,long calendarId,boolean enable){
        context.getSharedPreferences("accubook.calendar",Context.MODE_PRIVATE).edit()
            .putBoolean("enabled",enable).putLong("calendar",calendarId).apply();
    }
    public static void requirePermission(Context context) throws IOException {
        if(context.checkSelfPermission(Manifest.permission.READ_CALENDAR)!=
            PackageManager.PERMISSION_GRANTED ||
           context.checkSelfPermission(Manifest.permission.WRITE_CALENDAR)!=
            PackageManager.PERMISSION_GRANTED)
            throw new IOException("Grant calendar read/write permissions before enabling sync");
    }
    public List<CalendarChoice> choices() throws IOException {
        requirePermission(context);
        List<CalendarChoice> choices=new ArrayList<>();
        String[] projection={
            CalendarContract.Calendars._ID,
            CalendarContract.Calendars.CALENDAR_DISPLAY_NAME,
            CalendarContract.Calendars.ACCOUNT_NAME,
            CalendarContract.Calendars.CALENDAR_ACCESS_LEVEL
        };
        try(Cursor c=context.getContentResolver().query(CalendarContract.Calendars.CONTENT_URI,
            projection,CalendarContract.Calendars.VISIBLE+"=1",null,
            CalendarContract.Calendars.CALENDAR_DISPLAY_NAME+" ASC")){
            if(c==null)throw new IOException("Calendar provider unavailable");
            while(c.moveToNext()){
                if(c.getInt(3)>=CalendarContract.Calendars.CAL_ACCESS_CONTRIBUTOR)
                    choices.add(new CalendarChoice(c.getLong(0),
                        c.getString(1)==null?"Calendar":c.getString(1),
                        c.getString(2)==null?"Local":c.getString(2)));
            }
        }
        return choices;
    }
    private File linkFile(){return new File(store.root(),"master_data/calendar_links.csv");}
    private static List<String> row(String... v){return new ArrayList<>(Arrays.asList(v));}
    private List<List<String>> links() throws IOException {
        File file=linkFile();
        if(!file.isFile()&&!new File(file.getPath()+".bak").exists()){
            List<List<String>> fresh=new ArrayList<>();
            fresh.add(row(LINKS));
            writeLinks(fresh);
        }
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(InputStream in=new AtomicFile(file).openRead()){
            byte[] block=new byte[8192];int n;
            while((n=in.read(block))!=-1){
                if(bytes.size()+n>1024*1024)throw new IOException("Calendar mapping oversized");
                bytes.write(block,0,n);
            }
        }
        List<List<String>> lines=CsvCodec.read(bytes.toString("UTF-8"));
        if(lines.isEmpty()||!lines.get(0).equals(Arrays.asList(LINKS)))
            throw new IOException("Invalid calendar mapping CSV");
        for(List<String> line:lines)if(line.size()!=LINKS.length)
            throw new IOException("Bad calendar mapping row");
        return lines;
    }
    private void writeLinks(List<List<String>> lines) throws IOException {
        File file=linkFile();
        AtomicFile atomic=new AtomicFile(file);
        FileOutputStream out=null;
        try{
            out=atomic.startWrite();
            out.write(CsvCodec.write(lines).getBytes(StandardCharsets.UTF_8));
            atomic.finishWrite(out);
        }catch(IOException|RuntimeException e){
            if(out!=null)atomic.failWrite(out);
            throw e;
        }
    }
    private long previouslyLinked(List<List<String>> all,String jobId,long calendarId){
        for(int i=1;i<all.size();i++){
            List<String> row=all.get(i);
            if(row.get(0).equals(jobId)&&row.get(1).equals(Long.toString(calendarId)))
                try{return Long.parseLong(row.get(2));}catch(NumberFormatException ignored){}
        }
        return -1;
    }
    private long resolveExisting(ContentResolver resolver,String marker,long calendarId) {
        String[] projection={CalendarContract.Events._ID};
        try(Cursor c=resolver.query(CalendarContract.Events.CONTENT_URI,projection,
            CalendarContract.Events.CALENDAR_ID+"=? AND "+
                CalendarContract.Events.DESCRIPTION+" LIKE ?",
            new String[]{Long.toString(calendarId),"%"+marker+"%"},null)){
            if(c!=null&&c.moveToFirst())return c.getLong(0);
        }catch(Exception ignored){}
        return -1;
    }
    private ContentValues details(WorkspaceStore.Job job,long calendarId) throws IOException {
        CrmWorkspace.Appointment slot=crm.appointment(job);
        ZoneId timezone=ZoneId.systemDefault();
        long start=LocalDateTime.parse(job.date+"T"+slot.start)
            .atZone(timezone).toInstant().toEpochMilli();
        long end=LocalDateTime.parse(job.date+"T"+slot.end)
            .atZone(timezone).toInstant().toEpochMilli();
        if(end<=start)throw new IOException("Invalid calendar times");
        ContentValues values=new ContentValues();
        values.put(CalendarContract.Events.CALENDAR_ID,calendarId);
        values.put(CalendarContract.Events.TITLE,"Accubook · "+job.title);
        values.put(CalendarContract.Events.EVENT_LOCATION,
            job.street+", "+job.city+", "+job.state+" "+job.zip);
        // No customer phone or contact profile is copied into the calendar.
        values.put(CalendarContract.Events.DESCRIPTION,
            "Job status: "+job.status+"\nDaybook: "+slot.notes+
            "\nACCUBOOK-UID:"+job.id);
        values.put(CalendarContract.Events.DTSTART,start);
        values.put(CalendarContract.Events.DTEND,end);
        values.put(CalendarContract.Events.EVENT_TIMEZONE,timezone.getId());
        values.put(CalendarContract.Events.ACCESS_LEVEL,
            CalendarContract.Events.ACCESS_PRIVATE);
        return values;
    }
    /**
     * One-way reconciliation; can be called on schedule open and after edits.
     * Do not run from UI thread. Explicit calendar permission and consent required.
     */
    public synchronized int syncAll() throws IOException {
        if(!enabled(context))return 0;
        requirePermission(context);
        long calendarId=selectedCalendar(context);
        if(calendarId<0)throw new IOException("No calendar selected");
        boolean allowed=false;
        for(CalendarChoice c:choices())if(c.id==calendarId)allowed=true;
        if(!allowed)throw new IOException("Selected calendar cannot be written");
        List<List<String>> saved=links();
        List<WorkspaceStore.Job> jobs=store.jobs();
        if(jobs.size()>3000)throw new IOException("Bulk sync limit reached");
        ContentResolver resolver=context.getContentResolver();
        int count=0;
        for(WorkspaceStore.Job job:jobs){
            long id=previouslyLinked(saved,job.id,calendarId);
            ContentValues values=details(job,calendarId);
            String marker="ACCUBOOK-UID:"+job.id;
            if(id<0)id=resolveExisting(resolver,marker,calendarId);
            if(id>=0){
                Uri uri=ContentUris.withAppendedId(CalendarContract.Events.CONTENT_URI,id);
                int affected=resolver.update(uri,values,
                    CalendarContract.Events.CALENDAR_ID+"=?",
                    new String[]{Long.toString(calendarId)});
                if(affected==0)id=-1;
            }
            if(id<0){
                Uri created=resolver.insert(CalendarContract.Events.CONTENT_URI,values);
                if(created==null)throw new IOException("Calendar event insert failed");
                id=ContentUris.parseId(created);
            }
            int position=-1;
            for(int i=1;i<saved.size();i++)
                if(saved.get(i).get(0).equals(job.id)&&
                    saved.get(i).get(1).equals(Long.toString(calendarId)))position=i;
            List<String> mapping=row(job.id,Long.toString(calendarId),Long.toString(id));
            if(position<0)saved.add(mapping);else saved.set(position,mapping);
            writeLinks(saved);
            count++;
        }
        return count;
    }
}
