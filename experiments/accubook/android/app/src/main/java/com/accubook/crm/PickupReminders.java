package com.accubook.crm;

import android.Manifest;
import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.util.AtomicFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * User-initiated local dumpster-removal reminder. Inexact OS alarm:
 * battery management can delay delivery; no network service or exact-alarm exemption.
 */
public final class PickupReminders extends BroadcastReceiver {
    private static final String ACTION="com.accubook.crm.LOCAL_PICKUP";
    private static final String CHANNEL="accubook-pickup";
    private static final String[] HEADER={"DueAtUTC","ConfiguredAtUTC","State"};

    private static List<String> row(String... values){
        return new ArrayList<>(Arrays.asList(values));
    }
    private static File file(WorkspaceStore store,WorkspaceStore.Job job) throws IOException{
        return new File(store.directoryForJob(job),"pickup_reminder.csv");
    }
    private static void save(WorkspaceStore store,WorkspaceStore.Job job,
                             long due)throws IOException {
        File output=file(store,job);
        List<List<String>> data=new ArrayList<>();
        data.add(row(HEADER));
        data.add(row(Instant.ofEpochMilli(due).toString(),Instant.now().toString(),"Scheduled"));
        AtomicFile atomic=new AtomicFile(output);
        FileOutputStream stream=null;
        try{
            stream=atomic.startWrite();
            stream.write(CsvCodec.write(data).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            atomic.finishWrite(stream);
        }catch(IOException|RuntimeException e){
            if(stream!=null)atomic.failWrite(stream);
            throw e;
        }
    }
    private static long read(WorkspaceStore store,WorkspaceStore.Job job) throws IOException {
        File input=file(store,job);
        if(!input.isFile()&&!new File(input.getPath()+".bak").exists())return -1;
        try(InputStream in=new AtomicFile(input).openRead()) {
            byte[] raw=new byte[2048];
            int count=in.read(raw);
            if(count<=0)throw new IOException("Empty pickup reminder");
            List<List<String>> rows=CsvCodec.read(
                new String(raw,0,count,java.nio.charset.StandardCharsets.UTF_8));
            if(rows.size()!=2||!rows.get(0).equals(Arrays.asList(HEADER)))
                throw new IOException("Unexpected pickup reminder schema");
            return Instant.parse(rows.get(1).get(0)).toEpochMilli();
        }
    }
    public static long due(WorkspaceStore store,WorkspaceStore.Job job)throws IOException{
        return read(store,job);
    }
    private static PendingIntent pending(Context context,String jobId){
        Intent intent=new Intent(context,PickupReminders.class);
        intent.setAction(ACTION);
        intent.putExtra("jobId",jobId);
        return PendingIntent.getBroadcast(context,jobId.hashCode(),intent,
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    }
    private static void arm(Context context,String jobId,long due)throws IOException {
        AlarmManager alarms=(AlarmManager)context.getSystemService(Context.ALARM_SERVICE);
        if(alarms==null)throw new IOException("AlarmManager is unavailable");
        if(Build.VERSION.SDK_INT>=23)
            alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,due,pending(context,jobId));
        else alarms.set(AlarmManager.RTC_WAKEUP,due,pending(context,jobId));
    }
    public static synchronized void schedule(Context ctx,WorkspaceStore store,
                                             WorkspaceStore.Job job,long when)
        throws IOException {
        if(when<System.currentTimeMillis()+30_000)
            throw new IllegalArgumentException("Choose a future pickup time");
        save(store,job,when);
        arm(ctx,job.id,when);
    }
    public static synchronized void recover(Context ctx){
        // Android may discard alarms after reboot; rearm all pending future reminders.
        try {
            WorkspaceStore store=new WorkspaceStore(ctx);
            for(WorkspaceStore.Job job:store.jobs()){
                long when=read(store,job);
                if(when>System.currentTimeMillis())arm(ctx,job.id,when);
            }
        }catch(Exception failure){
            android.util.Log.e("Accubook","Local pickup reminders need review",failure);
        }
    }
    private static void notification(Context ctx){
        NotificationManager manager=(NotificationManager)ctx.getSystemService(
            Context.NOTIFICATION_SERVICE);
        if(manager==null)return;
        if(Build.VERSION.SDK_INT>=26){
            NotificationChannel channel=new NotificationChannel(CHANNEL,
                "Local contractor pickup reminders",NotificationManager.IMPORTANCE_DEFAULT);
            channel.setDescription("User-selected dumpster pickup reminder times");
            manager.createNotificationChannel(channel);
        }
        if(Build.VERSION.SDK_INT>=33&&ctx.checkSelfPermission(
            Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
            android.util.Log.w("Accubook","Pickup reminder notification permission denied");
            return;
        }
        Intent open=new Intent(ctx,MainActivity.class);
        PendingIntent openApp=PendingIntent.getActivity(ctx,0,open,
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder=Build.VERSION.SDK_INT>=26?
            new Notification.Builder(ctx,CHANNEL):new Notification.Builder(ctx);
        Notification message=builder.setSmallIcon(android.R.drawable.ic_popup_reminder)
            .setContentTitle("Accubook · Dumpster pickup due")
            .setContentText("Open Accubook to confirm the pickup and close the milestone.")
            .setContentIntent(openApp).setAutoCancel(true)
            .setVisibility(Notification.VISIBILITY_PRIVATE).build();
        manager.notify(124023,message);
    }
    @Override public void onReceive(Context ctx,Intent intent){
        if(intent==null)return;
        if(Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())){
            recover(ctx);return;
        }
        if(!ACTION.equals(intent.getAction()))return;
        String jobId=intent.getStringExtra("jobId");
        if(jobId==null)return;
        try{
            WorkspaceStore store=new WorkspaceStore(ctx);
            for(WorkspaceStore.Job job:store.jobs())
                if(job.id.equals(jobId)&&read(store,job)>0&&
                   read(store,job)<=System.currentTimeMillis()+60_000){
                    notification(ctx);return;
                }
        }catch(Exception error){android.util.Log.e("Accubook","Reminder delivery failed",error);}
    }
}
