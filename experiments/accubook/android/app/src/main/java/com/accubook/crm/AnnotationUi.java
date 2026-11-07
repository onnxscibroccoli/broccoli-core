package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.res.Resources;
import android.os.Build;
import android.os.PersistableBundle;
import android.text.InputType;
import android.text.InputFilter;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.ViewTreeObserver;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.WeakHashMap;
import java.util.function.Supplier;

/**
 * Development-only, local feedback interface. Does not intercept ordinary clicks,
 * replace existing long-press actions, capture screenshots or send telemetry.
 *
 * Existing long-press action menus add their own "Add annotation" option.
 * Leaves without a long-click action gain a non-destructive annotation shortcut.
 */
public final class AnnotationUi {
    public static final int EXPORT_JSON_REQUEST = 954;
    private static final WeakHashMap<View, String> SEMANTIC_KEYS = new WeakHashMap<>();

    private AnnotationUi() {}

    /** Optional stable binding for repeated rows, whose visual position may change. */
    public static void bind(View view, String key) {
        if (view != null && key != null && !key.isEmpty())
            synchronized (SEMANTIC_KEYS) { SEMANTIC_KEYS.put(view, key); }
    }

    /** Attach to dynamically built screens, including widgets added after setContentView. */
    public static void install(Activity activity, Supplier<String> screenSource) {
        View decor = activity.getWindow().getDecorView();
        WeakHashMap<View, Boolean> processed = new WeakHashMap<>();
        Runnable scan = () -> scan(activity, decor, processed, screenSource);
        decor.getViewTreeObserver().addOnGlobalLayoutListener(
            new ViewTreeObserver.OnGlobalLayoutListener() {
                @Override public void onGlobalLayout() { scan.run(); }
            });
        decor.post(scan);
    }

    private static void scan(Activity activity, View node,
            WeakHashMap<View, Boolean> processed, Supplier<String> screenSource) {
        if (node == null || node.getVisibility() != View.VISIBLE) return;
        if (!processed.containsKey(node)) {
            processed.put(node, true);
            // Long-click on editable fields is Android text selection; preserve it.
            // Long-clickable elements already implement drag/reorder/actions; never overwrite.
            boolean leaf = node instanceof TextView || node instanceof android.widget.ImageView
                || (node.hasOnClickListeners() && !(node instanceof ViewGroup));
            if (leaf && !(node instanceof EditText) && !node.isLongClickable()) {
                node.setOnLongClickListener(v -> {
                    String screen = screenSource.get();
                    if (screen == null || "locked".equals(screen)) return false;
                    annotateView(activity, screen, v);
                    return true;
                });
            }
        }
        if (node instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) node;
            for (int i = 0; i < group.getChildCount(); i++)
                scan(activity, group.getChildAt(i), processed, screenSource);
        }
    }

    private static String shortLabel(View view) {
        CharSequence title = view.getContentDescription();
        if ((title == null || title.length() == 0) && view instanceof TextView)
            title = ((TextView) view).getText();
        if (title == null) return "";
        String value = title.toString().trim().replace('\n', ' ');
        return value.length() > 200 ? value.substring(0, 200) : value;
    }

    /** Deterministic structural path; stable semantic keys are used where available. */
    private static String elementPath(View view) {
        StringBuilder result = new StringBuilder();
        View child = view;
        int depth = 0;
        while (child != null && depth++ < 25) {
            ViewParent parent = child.getParent();
            int index = 0;
            if (parent instanceof ViewGroup) {
                ViewGroup group = (ViewGroup) parent;
                for (int i = 0; i < group.getChildCount(); i++) {
                    View sibling = group.getChildAt(i);
                    if (sibling == child) break;
                    if (sibling.getClass().equals(child.getClass())) index++;
                }
            }
            String part = child.getClass().getSimpleName() + "[" + index + "]";
            result.insert(0, "/" + part);
            if (!(parent instanceof View)) break;
            child = (View) parent;
        }
        return result.length() > 500 ? result.substring(result.length() - 500) :
            result.toString();
    }

    private static void annotateView(Activity activity, String screen, View view) {
        String path = elementPath(view);
        String key;
        synchronized (SEMANTIC_KEYS) { key = SEMANTIC_KEYS.get(view); }
        if (key == null) {
            int id = view.getId();
            if (id != View.NO_ID) {
                try { key = "res:" + view.getResources().getResourceEntryName(id); }
                catch (Resources.NotFoundException ignored) { /* generated ID; use path */ }
            }
        }
        if (key == null) key = "path:" + path;
        edit(activity, screen, key, path, view.getClass().getSimpleName(),
            shortLabel(view));
    }

    /** Called by existing field/photo/invoice action menus without changing their gestures. */
    public static void edit(Activity activity, String screen, String key,
            String path, String widget, String label) {
        try {
            AnnotationStore store = new AnnotationStore(activity);
            List<AnnotationRecords.Entry> all = store.load();
            AnnotationRecords.Entry existing = AnnotationRecords.find(all, screen, key);
            LinearLayout box = new LinearLayout(activity);
            box.setPadding(28, 12, 28, 12);
            box.setOrientation(LinearLayout.VERTICAL);
            TextView about = new TextView(activity);
            about.setText("Element: " + label + "\n" + screen +
                "\nPrivate on this device until you copy or export.");
            box.addView(about);
            EditText note = new EditText(activity);
            note.setHint("What should change? What happened? What did you expect?");
            note.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE |
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
            note.setSingleLine(false);
            note.setMinLines(4);
            note.setMaxLines(12);
            note.setFilters(new InputFilter[]{new InputFilter.LengthFilter(AnnotationRecords.MAX_NOTE)});
            note.setText(existing == null ? "" : existing.note);
            note.setSelection(note.length());
            box.addView(note);
            AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle(existing == null ? "Add annotation" : "Edit annotation")
                .setView(box)
                .setNegativeButton("Cancel", (d, w) -> {})
                .setNeutralButton(existing == null ? "Keep empty" : "Delete", (d, w) -> {
                    if (existing == null) return;
                    new AlertDialog.Builder(activity).setTitle("Delete this annotation?")
                        .setMessage("This removes only the private testing note.")
                        .setNegativeButton("Keep", (dd, w2) -> {})
                        .setPositiveButton("Delete", (dd, w2) -> {
                            try {
                                store.save(AnnotationRecords.delete(store.load(), screen, key));
                                Toast.makeText(activity, "Annotation deleted", Toast.LENGTH_SHORT).show();
                            } catch (Exception error) { failure(activity, error); }
                        }).show();
                })
                .setPositiveButton("Save", null).create();
            dialog.setOnShowListener(d ->
                dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                    String value = note.getText().toString().trim();
                    if (value.isEmpty()) {
                        note.setError("Enter a note, or choose Cancel/Delete");
                        return;
                    }
                    try {
                        List<AnnotationRecords.Entry> entries = store.load();
                        store.save(AnnotationRecords.upsert(entries,
                            java.util.UUID.randomUUID().toString(), screen, key, path, widget,
                            label == null ? "" : label, value, Instant.now().toString()));
                        dialog.dismiss();
                        Toast.makeText(activity, "Saved privately", Toast.LENGTH_SHORT).show();
                    } catch (Exception error) { failure(activity, error); }
                }));
            dialog.show();
        } catch (Exception error) { failure(activity, error); }
    }

    private static void failure(Activity activity, Exception error) {
        new AlertDialog.Builder(activity).setTitle("Annotation not saved")
            .setMessage(error.getMessage() == null ? "Local storage error" : error.getMessage())
            .setPositiveButton("OK", (d, w) -> {}).show();
    }

    /** Explicit owner export: never an automatic share, telemetry event or upload. */
    public static void exportDialog(Activity activity) {
        try {
            List<AnnotationRecords.Entry> entries = new AnnotationStore(activity).load();
            String json = AnnotationRecords.toJson(entries, Instant.now().toString());
            TextView info = new TextView(activity);
            info.setPadding(28, 18, 28, 12);
            info.setText(entries.size() + " annotations. JSON includes your notes and screen " +
                "labels, which may contain customer details. Copy or save only if you intend " +
                "to paste/share it. Nothing is sent automatically.\n\n" +
                (json.length() > 9000 ? json.substring(0, 9000) +
                    "\n… (preview truncated; Copy/Save includes the entire JSON)" : json));
            info.setTextIsSelectable(true);
            ScrollView scroll = new ScrollView(activity);
            scroll.addView(info);
            AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("Development annotations · local JSON")
                .setView(scroll)
                .setNegativeButton("Close", (d, w) -> {})
                .setNeutralButton("Save JSON file", (d, w) -> {
                    Intent document = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    document.addCategory(Intent.CATEGORY_OPENABLE);
                    document.setType("application/json");
                    document.putExtra(Intent.EXTRA_TITLE,
                        "accubook-feedback-" + LocalDate.now() + ".json");
                    try { activity.startActivityForResult(document, EXPORT_JSON_REQUEST); }
                    catch (Exception error) { failure(activity, error); }
                })
                .setPositiveButton("Copy JSON", (d, w) -> {
                    ClipboardManager clipboard = (ClipboardManager)
                        activity.getSystemService(Context.CLIPBOARD_SERVICE);
                    ClipData clip = ClipData.newPlainText("Accubook development annotations", json);
                    if (Build.VERSION.SDK_INT >= 33) {
                        PersistableBundle extras = new PersistableBundle();
                        extras.putBoolean(android.content.ClipDescription.EXTRA_IS_SENSITIVE, true);
                        clip.getDescription().setExtras(extras);
                    }
                    clipboard.setPrimaryClip(clip);
                    Toast.makeText(activity, "Copied JSON; paste into ChatGPT when ready",
                        Toast.LENGTH_LONG).show();
                }).create();
            dialog.show();
        } catch (Exception error) { failure(activity, error); }
    }

    /** Call from the dashboard Activity's onActivityResult after the SAF picker. */
    public static boolean handleExportResult(Activity activity,
            int requestCode, int resultCode, Intent data) {
        if (requestCode != EXPORT_JSON_REQUEST) return false;
        if (resultCode != Activity.RESULT_OK || data == null || data.getData() == null)
            return true;
        try {
            String json = AnnotationRecords.toJson(
                new AnnotationStore(activity).load(), Instant.now().toString());
            try (OutputStream out = activity.getContentResolver().openOutputStream(data.getData())) {
                if (out == null) throw new java.io.IOException("Cannot open selected JSON file");
                out.write(json.getBytes(StandardCharsets.UTF_8));
            }
            Toast.makeText(activity, "JSON saved to the selected document", Toast.LENGTH_LONG).show();
        } catch (Exception error) { failure(activity, error); }
        return true;
    }
}
