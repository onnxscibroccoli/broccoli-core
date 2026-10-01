package org.omnikali.rdcsupervisor;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;

final class RecoveryCoordinator {
    private static final String TERMUX = "com.termux";

    private RecoveryCoordinator() {}

    static boolean securityGatesSatisfied(Context context) {
        return context.checkSelfPermission("com.termux.permission.RUN_COMMAND")
                == PackageManager.PERMISSION_GRANTED;
    }

    static void requestTermuxSupervisorReconcile(Context context) {
        Intent intent = new Intent("com.termux.RUN_COMMAND");
        intent.setComponent(new ComponentName(
                TERMUX, "com.termux.app.RunCommandService"));
        intent.putExtra("com.termux.RUN_COMMAND_PATH",
                "/data/data/com.termux/files/usr/bin/bash");
        intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS",
                new String[]{"-lc", SupervisorBootstrap.COMMAND});
        intent.putExtra("com.termux.RUN_COMMAND_WORKDIR",
                "/data/data/com.termux/files/home");
        intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true);
        intent.putExtra("com.termux.RUN_COMMAND_COMMAND_LABEL",
                "OmniKali Recovery Reconcile");
        try {
            context.startService(intent);
        } catch (Throwable error) {
            RecoveryJournal.append(
                    context, "TERMUX_RECONCILE_ERROR",
                    error.getClass().getSimpleName());
        }
    }

    static final class SupervisorBootstrap {
        static final String COMMAND =
                "set -eu; "
                + "STATE=$HOME/.omnikali/rdc-supervisor; "
                + "mkdir -p $STATE; "
                + "if [ -f $STATE/supervisord.conf ]; then "
                + "supervisorctl -c $STATE/supervisord.conf status >/dev/null 2>&1 "
                + "|| supervisord -c $STATE/supervisord.conf; "
                + "else "
                + "printf '%s\\n' CONFIG_MISSING > $STATE/status; "
                + "fi";
    }
}
