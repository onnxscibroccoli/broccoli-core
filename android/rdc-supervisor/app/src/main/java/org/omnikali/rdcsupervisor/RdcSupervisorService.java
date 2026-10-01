package org.omnikali.rdcsupervisor;

import android.app.ActivityManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.IBinder;
import android.os.SystemClock;

import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public final class RdcSupervisorService extends Service {
    private static final String TERMUX = "com.termux";
    private static final String CHANNEL = "omnikali_rdc_supervisor";
    private static final int NOTIFICATION_ID = 4401;
    private static final long POLL_MS = 15_000L;
    private static final long RESTART_BACKOFF_MS = 60_000L;

    private ScheduledExecutorService executor;
    private long lastRecoveryElapsed = Long.MIN_VALUE;

    public static void start(Context context) {
        Intent intent = new Intent(context, RdcSupervisorService.class);
        try {
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(intent);
            else context.startService(intent);
        } catch (RuntimeException ignored) {
            // Android background-start policy is fail-closed.
        }
    }

    @Override public void onCreate() {
        super.onCreate();
        createChannel();

        Notification notification = new Notification.Builder(this, CHANNEL)
                .setContentTitle("OmniKali RDC Supervisor")
                .setContentText("Reconciling Termux and Remote Desktop Commander")
                .setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setOngoing(true)
                .build();

        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification,
                    android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }

        executor = Executors.newSingleThreadScheduledExecutor();
        executor.scheduleWithFixedDelay(this::tick, 0, POLL_MS, TimeUnit.MILLISECONDS);
    }

    private void tick() {
        try {
            boolean termuxVisible = isTermuxRunningBestEffort();
            long now = SystemClock.elapsedRealtime();

            // Process visibility is diagnostic, not authoritative. Reconcile the
            // desired RDC state on every tick. The Termux-side command is idempotent:
            // it starts RDC only when no matching remote process exists.
            if (!termuxVisible || now - lastRecoveryElapsed >= RESTART_BACKOFF_MS) {
                reconcileRemote();
            }
        } catch (Throwable ignored) {
            // A failed probe must never kill the watchdog.
        }
    }

    private boolean isTermuxRunningBestEffort() {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        List<ActivityManager.RunningAppProcessInfo> processes =
                manager.getRunningAppProcesses();
        if (processes == null) return false;

        for (ActivityManager.RunningAppProcessInfo process : processes) {
            if (TERMUX.equals(process.processName)) return true;
        }
        return false;
    }

    private void reconcileRemote() {
        if (checkSelfPermission("com.termux.permission.RUN_COMMAND")
                != PackageManager.PERMISSION_GRANTED) return;

        Intent intent = new Intent("com.termux.RUN_COMMAND");
        intent.setComponent(new ComponentName(
                TERMUX, "com.termux.app.RunCommandService"));
        intent.putExtra("com.termux.RUN_COMMAND_PATH",
                "/data/data/com.termux/files/usr/bin/bash");
        intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS",
                new String[]{"-lc", RecoveryCommand.COMMAND});
        intent.putExtra("com.termux.RUN_COMMAND_WORKDIR",
                "/data/data/com.termux/files/home");
        intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true);
        intent.putExtra("com.termux.RUN_COMMAND_COMMAND_LABEL",
                "OmniKali RDC Supervisor");

        try {
            startService(intent);
            lastRecoveryElapsed = SystemClock.elapsedRealtime();
        } catch (SecurityException ignored) {
            // RUN_COMMAND or Termux external-app policy is not satisfied.
        } catch (RuntimeException ignored) {
            // Termux may be transitioning between process states.
        }
    }

    private void createChannel() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(
                CHANNEL, "OmniKali RDC Supervisor",
                NotificationManager.IMPORTANCE_LOW));
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override public void onDestroy() {
        if (executor != null) executor.shutdownNow();
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    static final class RecoveryCommand {
        static final String COMMAND =
                "set -eu; " +
                "STATE=\"$HOME/.omnikali/rdc-supervisor\"; " +
                "mkdir -p \"$STATE\"; " +
                "if mkdir \"$STATE/.lock\" 2>/dev/null; then " +
                "trap 'rmdir \"$STATE/.lock\" 2>/dev/null || true' EXIT; " +
                "date +%s > \"$STATE/last-supervisor-invoke\"; " +
                "if pgrep -f 'node .*desktop-commander remote' >/dev/null 2>&1; then " +
                "printf '%s\\n' ALREADY_RUNNING > \"$STATE/status\"; " +
                "else " +
                "nohup npx --yes @wonderwhy-er/desktop-commander@latest remote " +
                ">> \"$STATE/remote.log\" 2>&1 & " +
                "echo $! > \"$STATE/remote.pid\"; " +
                "printf '%s\\n' STARTED > \"$STATE/status\"; " +
                "fi; fi";
    }
}
