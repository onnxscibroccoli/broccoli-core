package com.ian.roofmeasure;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.Context;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.content.pm.PackageManager;
import android.webkit.JavascriptInterface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.content.pm.ApplicationInfo;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.GeolocationPermissions;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import android.content.ContentValues;
import android.content.ClipData;
import android.provider.MediaStore;
import android.print.RmPdfWriter;
import java.util.HashMap;
import java.util.Map;

/** Minimal WebView shell. Bundled assets/www/ are served from a virtual HTTPS origin
 *  (https://appassets.androidplatform.net/www/...) so the page is a secure context
 *  (geolocation, CORS with a real Origin) without any androidx dependency. */
public class MainActivity extends Activity {
    static final String HOST = "appassets.androidplatform.net";
    static final String START = "https://" + HOST + "/www/index.html";
    static final int REQ_LOC = 42;
    WebView web;
    GeolocationPermissions.Callback pendingCb;
    String pendingOrigin;
    WebView printView; // kept referenced until the print job is queued (GC would cancel it)

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setGeolocationEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setUserAgentString(s.getUserAgentString() + " RoofMeasureAndroid/0.1.7.6");
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if (!"https".equals(u.getScheme()) || !HOST.equals(u.getHost())) return null;
                String p = u.getPath();
                if (p == null || !p.startsWith("/www/") || p.contains("..")) return notFound();
                try {
                    InputStream in = getAssets().open(p.substring(1));
                    WebResourceResponse res = new WebResourceResponse(mime(p), "utf-8", in);
                    Map<String, String> h = new HashMap<>();
                    h.put("Access-Control-Allow-Origin", "*");
                    h.put("Cache-Control", "no-cache");
                    res.setResponseHeaders(h);
                    return res;
                } catch (Exception e) { return notFound(); }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                String sch = r.getUrl().getScheme();
                return !("https".equals(sch)); // block http:, intent:, file: navigations
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage m) {
                Log.i("RoofMeasureJS", m.messageLevel() + " " + m.sourceId() + ":" + m.lineNumber() + " " + m.message());
                return true;
            }
            @Override public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback cb) {
                if (hasLoc()) { cb.invoke(origin, true, false); return; }
                pendingOrigin = origin; pendingCb = cb;
                if (Build.VERSION.SDK_INT >= 23)
                    requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_LOC);
            }
        });
        web.addJavascriptInterface(new Bridge(), "RoofBridge");
        // debug builds only: CI smoke test passes the page query (e.g. addr=...&smoke=1) as an intent extra
        String q = null;
        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0 && getIntent() != null) q = getIntent().getStringExtra("rm_query");
        if (q != null && q.matches("[A-Za-z0-9=&%._,+-]{1,300}")) web.loadUrl(START + "?" + q);
        else if (b != null) web.restoreState(b); else web.loadUrl(START);
    }

    /** window.RoofBridge.save(name, text): WebView ignores blob downloads, so hand exports to the share sheet
     *  (Drive, Gmail, Files, Messages...). Text only; no file/storage permission needed. */
    class Bridge {
        @JavascriptInterface public void printHtml(final String html, final String jobName) {
            runOnUiThread(new Runnable() { public void run() { printReport(html, jobName); } });
        }
        /** 0.1.7.1: write the report PDF to a file, then share it (share sheet) or copy it to Downloads. */
        @JavascriptInterface public void sharePdf(final String html, final String jobName) {
            runOnUiThread(new Runnable() { public void run() { makePdf(html, jobName, "share"); } });
        }
        @JavascriptInterface public void savePdf(final String html, final String jobName) {
            runOnUiThread(new Runnable() { public void run() {
                if (Build.VERSION.SDK_INT < 29) { printReport(html, jobName); notifyJs("save", true, "Android < 10: use Save as PDF in the print dialog"); return; }
                makePdf(html, jobName, "save"); } });
        }
        @JavascriptInterface public String version() { return "0.1.7.6"; }
        @JavascriptInterface public void save(final String name, final String text) {
            runOnUiThread(new Runnable() { public void run() {
                Intent i = new Intent(Intent.ACTION_SEND);
                i.setType(name != null && name.endsWith(".csv") ? "text/csv" : "text/plain");
                i.putExtra(Intent.EXTRA_SUBJECT, name);
                i.putExtra(Intent.EXTRA_TITLE, name);
                i.putExtra(Intent.EXTRA_TEXT, text);
                startActivity(Intent.createChooser(i, "Export " + name));
            }});
        }
    }

    /** In-app PDF report: render the report HTML in an offscreen WebView and hand it to PrintManager
     *  (WebView.createPrintDocumentAdapter = same Chromium print engine as desktop Chrome). User picks "Save as PDF". */
    static String safeName(String n) {
        String s = (n == null || n.isEmpty()) ? "RoofMeasure_report" : n.replaceAll("[^A-Za-z0-9._-]+", "_");
        return s.length() > 80 ? s.substring(0, 80) : s;
    }
    void notifyJs(String kind, boolean ok, String msg) {
        final String js = "window.RoofReportNative&&window.RoofReportNative(" + q(kind) + "," + ok + "," + q(msg) + ")";
        runOnUiThread(new Runnable() { public void run() { web.evaluateJavascript(js, null); } });
    }
    static String q(String s) {
        StringBuilder b = new StringBuilder("\"");
        for (char c : String.valueOf(s).toCharArray()) {
            if (c == '"' || c == '\\') b.append('\\').append(c); else if (c < 0x20 || c == 0x2028 || c == 0x2029) b.append(String.format("\\u%04x", (int) c)); else b.append(c);
        }
        return b.append('"').toString();
    }
    WebView pdfView; // referenced until the file is written
    void makePdf(final String html, final String jobName, final String kind) {
        final String name = safeName(jobName);
        final File dir = new File(getCacheDir(), "reports");
        dir.mkdirs();
        final File out = new File(dir, name + ".pdf");
        final WebView pv = new WebView(this);
        pv.getSettings().setJavaScriptEnabled(false);
        pv.getSettings().setAllowFileAccess(false);
        pv.getSettings().setAllowContentAccess(false);
        pv.setWebViewClient(new WebViewClient() {
            boolean started = false;
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return true; }
            @Override public void onPageFinished(WebView v, String url) {
                if (started) return; started = true; // onPageFinished can fire more than once
                RmPdfWriter.write(v.createPrintDocumentAdapter(name), out, new RmPdfWriter.Done() {
                    public void done(final boolean ok, final String msg) {
                        runOnUiThread(new Runnable() { public void run() {
                            pdfView = null;
                            if (!ok) { notifyJs(kind, false, "PDF not written (" + msg + "); falling back to the print dialog"); printReport(html, name); return; }
                            if ("share".equals(kind)) sharePdfFile(out); else savePdfToDownloads(out);
                        } });
                    }
                });
            }
        });
        pdfView = pv;
        pv.loadDataWithBaseURL("https://" + HOST + "/report/", html, "text/html", "utf-8", null);
    }
    void sharePdfFile(File f) {
        try {
            Uri u = ReportProvider.uriFor(f);
            Intent i = new Intent(Intent.ACTION_SEND);
            i.setType("application/pdf");
            i.putExtra(Intent.EXTRA_STREAM, u);
            i.putExtra(Intent.EXTRA_SUBJECT, f.getName());
            i.setClipData(ClipData.newRawUri(f.getName(), u));
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(i, "Share " + f.getName()));
            notifyJs("share", true, "PDF ready (" + (f.length() / 1024) + " KB): pick an app to share it.");
        } catch (Exception e) { notifyJs("share", false, "share failed: " + e); }
    }
    void savePdfToDownloads(File f) {
        try {
            ContentValues v = new ContentValues();
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, f.getName());
            v.put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf");
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, "Download/RoofMeasure");
            Uri u = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
            if (u == null) throw new Exception("MediaStore insert returned null");
            OutputStream os = getContentResolver().openOutputStream(u);
            InputStream is = new FileInputStream(f);
            byte[] buf = new byte[65536]; int n;
            while ((n = is.read(buf)) > 0) os.write(buf, 0, n);
            is.close(); os.close();
            notifyJs("save", true, "Saved to Downloads/RoofMeasure/" + f.getName() + " (" + (f.length() / 1024) + " KB).");
        } catch (Exception e) { notifyJs("save", false, "save failed: " + e + " — use Share PDF instead"); }
    }

    void printReport(final String html, final String jobName) {
        final WebView pv = new WebView(this);
        pv.getSettings().setJavaScriptEnabled(false);
        pv.getSettings().setAllowFileAccess(false);
        pv.getSettings().setAllowContentAccess(false);
        pv.setWebViewClient(new WebViewClient() {
            boolean printed = false;
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return true; }
            @Override public void onPageFinished(WebView v, String url) {
                if (printed) return; printed = true; // onPageFinished can fire more than once -> duplicate print jobs
                PrintManager pm = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                String name = (jobName == null || jobName.isEmpty()) ? "RoofMeasure_report" : jobName;
                PrintDocumentAdapter ad = Build.VERSION.SDK_INT >= 21 ? v.createPrintDocumentAdapter(name) : v.createPrintDocumentAdapter();
                PrintAttributes attrs = new PrintAttributes.Builder()
                    .setMediaSize(PrintAttributes.MediaSize.NA_LETTER)
                    .setMinMargins(PrintAttributes.Margins.NO_MARGINS).build();
                pm.print(name, ad, attrs);
            }
        });
        printView = pv;
        pv.loadDataWithBaseURL("https://" + HOST + "/report/", html, "text/html", "utf-8", null);
    }

    boolean hasLoc() {
        return Build.VERSION.SDK_INT < 23
            || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
            || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    @Override public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        if (code == REQ_LOC && pendingCb != null) {
            pendingCb.invoke(pendingOrigin, hasLoc(), false);
            pendingCb = null; pendingOrigin = null;
        }
    }

    static WebResourceResponse notFound() {
        WebResourceResponse r = new WebResourceResponse("text/plain", "utf-8", null);
        r.setStatusCodeAndReasonPhrase(404, "Not Found");
        return r;
    }

    static String mime(String p) {
        if (p.endsWith(".html")) return "text/html";
        if (p.endsWith(".js")) return "application/javascript";
        if (p.endsWith(".css")) return "text/css";
        if (p.endsWith(".json")) return "application/json";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".svg")) return "image/svg+xml";
        if (p.endsWith(".wasm")) return "application/wasm";
        if (p.endsWith(".mjs")) return "application/javascript";
        return "application/octet-stream";
    }

    @Override protected void onSaveInstanceState(Bundle o) { super.onSaveInstanceState(o); web.saveState(o); }
    @Override public void onBackPressed() { if (web.canGoBack()) web.goBack(); else super.onBackPressed(); }
}
