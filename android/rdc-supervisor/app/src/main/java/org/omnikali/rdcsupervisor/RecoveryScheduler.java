package org.omnikali.rdcsupervisor;

import android.content.Context;

import androidx.work.BackoffPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;

import java.util.concurrent.TimeUnit;

final class RecoveryScheduler {
    private static final String UNIQUE_NAME = "omnikali-recovery-reconcile";

    private RecoveryScheduler() {}

    static void enqueue(Context context) {
        OneTimeWorkRequest request =
                new OneTimeWorkRequest.Builder(RecoveryReconciliationWorker.class)
                        .setBackoffCriteria(
                                BackoffPolicy.EXPONENTIAL,
                                15, TimeUnit.SECONDS)
                        .addTag(UNIQUE_NAME)
                        .build();
        WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_NAME, ExistingWorkPolicy.KEEP, request);
    }
}
