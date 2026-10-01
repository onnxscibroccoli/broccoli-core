package org.omnikali.rdcsupervisor;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(action)
                || Intent.ACTION_LOCKED_BOOT_COMPLETED.equals(action)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) {
            RecoveryJournal.append(
                    context, "BOOT_OR_REPLACEMENT", String.valueOf(action));
            RecoveryScheduler.enqueue(context);
            RdcSupervisorService.start(context);
        }
    }
}
