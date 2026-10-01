package org.omnikali.rdcsupervisor;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32, 32, 32, 32);

        status = new TextView(this);
        root.addView(status);

        Button supervisorInfo = new Button(this);
        supervisorInfo.setText("Open Supervisor App Info");
        supervisorInfo.setOnClickListener(v -> openAppInfo(getPackageName()));
        root.addView(supervisorInfo);

        Button termuxInfo = new Button(this);
        termuxInfo.setText("Open Termux App Info");
        termuxInfo.setOnClickListener(v -> openAppInfo("com.termux"));
        root.addView(termuxInfo);

        Button start = new Button(this);
        start.setText("Start Supervisor");
        start.setOnClickListener(v -> {
            RdcSupervisorService.start(this);
            RecoveryScheduler.enqueue(this);
            refresh();
        });
        root.addView(start);

        setContentView(root);
        RdcSupervisorService.start(this);
        RecoveryScheduler.enqueue(this);
        refresh();
    }

    @Override protected void onResume() {
        super.onResume();
        RecoveryScheduler.enqueue(this);
        refresh();
    }

    private void openAppInfo(String packageName) {
        startActivity(new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + packageName)));
    }

    private void refresh() {
        boolean granted = checkSelfPermission(
                "com.termux.permission.RUN_COMMAND")
                == android.content.pm.PackageManager.PERMISSION_GRANTED;
        status.setText("OmniKali RDC Supervisor\n\nRUN_COMMAND permission: "
                + (granted ? "GRANTED" : "MISSING")
                + "\n\nTermux must also have allow-external-apps=true."
                + "\n\nAndroid supervisor: foreground watchdog"
                + "\nWorkManager: persistent reconciliation/checkpoint"
                + "\nTermux: supervisord owns individual services.");
    }
}
