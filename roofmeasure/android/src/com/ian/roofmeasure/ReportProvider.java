// SPDX-License-Identifier: MIT
package com.ian.roofmeasure;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;

/** Read-only provider for generated report PDFs in cacheDir/reports (no androidx FileProvider needed).
 *  Not exported; share targets get a one-off grant via FLAG_GRANT_READ_URI_PERMISSION. */
public class ReportProvider extends ContentProvider {
    static final String AUTH = "com.ian.roofmeasure.reports";
    static Uri uriFor(File f) { return Uri.parse("content://" + AUTH + "/" + Uri.encode(f.getName())); }
    File fileFor(Uri u) throws FileNotFoundException {
        String n = u.getLastPathSegment();
        if (n == null || n.contains("/") || n.contains("..") || !n.endsWith(".pdf")) throw new FileNotFoundException("bad name");
        File f = new File(new File(getContext().getCacheDir(), "reports"), n);
        if (!f.isFile()) throw new FileNotFoundException(n);
        return f;
    }
    @Override public boolean onCreate() { return true; }
    @Override public String getType(Uri u) { return "application/pdf"; }
    @Override public ParcelFileDescriptor openFile(Uri u, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("read-only");
        return ParcelFileDescriptor.open(fileFor(u), ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public Cursor query(Uri u, String[] proj, String sel, String[] args, String sort) {
        File f; try { f = fileFor(u); } catch (FileNotFoundException e) { return null; }
        MatrixCursor c = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
        c.addRow(new Object[]{f.getName(), f.length()});
        return c;
    }
    @Override public Uri insert(Uri u, ContentValues v) { return null; }
    @Override public int delete(Uri u, String s, String[] a) { return 0; }
    @Override public int update(Uri u, ContentValues v, String s, String[] a) { return 0; }
}
