package org.omnikali.rdcsupervisor;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

public final class RecoveryReconciliationWorker extends Worker {
    public RecoveryReconciliationWorker(
            @NonNull android.content.Context context,
            @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        RecoveryJournal.append(
                getApplicationContext(),
                "WORK_MANAGER_RECONCILE",
                "persistent reconciliation checkpoint");

        if (!RecoveryCoordinator.securityGatesSatisfied(getApplicationContext())) {
            RecoveryJournal.append(
                    getApplicationContext(),
                    "WORK_MANAGER_BLOCKED",
                    "RUN_COMMAND permission is not satisfied");
            return Result.success();
        }

        RecoveryCoordinator.requestTermuxSupervisorReconcile(getApplicationContext());
        RecoveryJournal.append(
                getApplicationContext(),
                "WORK_MANAGER_RECONCILE_REQUESTED",
                "Termux supervisor reconciliation requested");
        return Result.success();
    }
}
