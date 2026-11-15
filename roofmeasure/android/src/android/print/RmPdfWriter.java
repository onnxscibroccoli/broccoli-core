// SPDX-License-Identifier: MIT
package android.print;

import android.os.CancellationSignal;
import android.os.ParcelFileDescriptor;
import java.io.File;

/** Writes a WebView PrintDocumentAdapter straight to a PDF file (no print dialog).
 *  Lives in android.print because LayoutResultCallback/WriteResultCallback constructors are package-private. */
public final class RmPdfWriter {
    public interface Done { void done(boolean ok, String msg); }
    private RmPdfWriter() {}

    public static void write(final PrintDocumentAdapter ad, final File out, final Done cb) {
        final PrintAttributes attrs = new PrintAttributes.Builder()
            .setMediaSize(PrintAttributes.MediaSize.NA_LETTER)
            .setResolution(new PrintAttributes.Resolution("rm", "pdf", 300, 300))
            .setColorMode(PrintAttributes.COLOR_MODE_COLOR)
            .setMinMargins(PrintAttributes.Margins.NO_MARGINS).build();
        try {
            ad.onStart();
            ad.onLayout(null, attrs, new CancellationSignal(), new PrintDocumentAdapter.LayoutResultCallback() {
                @Override public void onLayoutFinished(PrintDocumentInfo info, boolean changed) {
                    final ParcelFileDescriptor pfd;
                    try {
                        pfd = ParcelFileDescriptor.open(out, ParcelFileDescriptor.MODE_CREATE | ParcelFileDescriptor.MODE_TRUNCATE | ParcelFileDescriptor.MODE_READ_WRITE);
                    } catch (Exception e) { finish(ad); cb.done(false, "open " + out + ": " + e); return; }
                    ad.onWrite(new PageRange[]{PageRange.ALL_PAGES}, pfd, new CancellationSignal(), new PrintDocumentAdapter.WriteResultCallback() {
                        @Override public void onWriteFinished(PageRange[] pages) { close(pfd); finish(ad); cb.done(out.length() > 0, out.length() > 0 ? "ok" : "empty PDF"); }
                        @Override public void onWriteFailed(CharSequence err) { close(pfd); finish(ad); cb.done(false, "write failed: " + err); }
                        @Override public void onWriteCancelled() { close(pfd); finish(ad); cb.done(false, "write cancelled"); }
                    });
                }
                @Override public void onLayoutFailed(CharSequence err) { finish(ad); cb.done(false, "layout failed: " + err); }
                @Override public void onLayoutCancelled() { finish(ad); cb.done(false, "layout cancelled"); }
            }, null);
        } catch (Throwable t) { finish(ad); cb.done(false, "pdf error: " + t); }
    }
    static void close(ParcelFileDescriptor p) { try { p.close(); } catch (Exception e) { /* ignore */ } }
    static void finish(PrintDocumentAdapter ad) { try { ad.onFinish(); } catch (Throwable t) { /* ignore */ } }
}
