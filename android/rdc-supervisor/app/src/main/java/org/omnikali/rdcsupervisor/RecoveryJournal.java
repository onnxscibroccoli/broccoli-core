package org.omnikali.rdcsupervisor;

import android.content.Context;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class RecoveryJournal {
    private RecoveryJournal() {}

    static synchronized void append(Context context, String event, String detail) {
        try {
            File root = new File(context.getExternalFilesDir(null), "recovery");
            if (!root.exists() && !root.mkdirs()) return;
            File file = new File(root, "events.jsonl");
            String timestamp = new SimpleDateFormat(
                    "yyyy-MM-dd'T'HH:mm:ss.SSSXXX", Locale.US).format(new Date());
            String safe = detail.replace("\\", "\\\\").replace(""", "\\"");
            String line = "{"ts":"" + timestamp + "","event":""
                    + event + "","detail":"" + safe + ""}\n";
            try (FileOutputStream out = new FileOutputStream(file, true)) {
                out.write(line.getBytes(StandardCharsets.UTF_8));
                out.getFD().sync();
            }
        } catch (Throwable ignored) {
            // Evidence must never crash the supervisor.
        }
    }
}
