package com.accubook.crm;

import android.content.Context;
import android.util.AtomicFile;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Local private app files only. Explicit JSON export never happens here.
 * Deliberately separate from customer workspace ZIPs, sharing and restore.
 */
public final class AnnotationStore {
    private static final int MAX_BYTES = 2 * 1024 * 1024;
    private final AtomicFile file;

    public AnnotationStore(Context context) {
        file = new AtomicFile(new File(context.getFilesDir(), "accubook-test-annotations.csv"));
    }

    public synchronized List<AnnotationRecords.Entry> load() throws IOException {
        File base = file.getBaseFile();
        if (!base.isFile() && !new File(base.getPath() + ".bak").isFile())
            return new java.util.ArrayList<>();
        try (InputStream in = file.openRead(); ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
            byte[] data = new byte[4096];
            int count;
            while ((count = in.read(data)) != -1) {
                if (buffer.size() + count > MAX_BYTES)
                    throw new IOException("Annotations file exceeds the 2 MB safety limit");
                buffer.write(data, 0, count);
            }
            String csv;
            try {
                csv = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(buffer.toByteArray())).toString();
            } catch (CharacterCodingException invalid) {
                throw new IOException("Annotations are not valid UTF-8", invalid);
            }
            return AnnotationRecords.read(csv);
        }
    }

    public synchronized void save(List<AnnotationRecords.Entry> entries) throws IOException {
        byte[] bytes = AnnotationRecords.write(entries).getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_BYTES) throw new IOException("Annotation limit exceeded (2 MB)");
        FileOutputStream out = null;
        try {
            out = file.startWrite();
            out.write(bytes);
            file.finishWrite(out);
        } catch (IOException | RuntimeException failure) {
            if (out != null) file.failWrite(out);
            throw failure;
        }
    }
}
