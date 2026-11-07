package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DatePickerDialog;
import android.app.TimePickerDialog;
import android.Manifest;
import android.content.pm.PackageManager;
import android.provider.OpenableColumns;
import android.content.ClipData;
import android.widget.CheckBox;
import android.widget.Toast;
import android.graphics.Typeface;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.HashSet;
import java.util.Map;
import java.math.BigDecimal;
import java.time.LocalTime;
import java.io.FileInputStream;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.provider.ContactsContract;
import android.text.Editable;
import android.text.TextWatcher;
import android.widget.ImageView;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.IOException;
import java.io.OutputStream;
import java.io.InputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.DayOfWeek;
import java.time.temporal.TemporalAdjusters;
import java.util.List;

/** Offline debug UI. No remote permissions, services or privileged APIs. */
public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 702;
    private static final int CONTACT_REQUEST = 703;
    private static final int PHOTO_REQUEST = 704;
    private static final int RESTORE_REQUEST = 705;
    private static final int ATTACHMENT_REQUEST = 706;
    private static final int LOGO_REQUEST = 707;
    private static final int ATTACHMENT_EXPORT_REQUEST = 708;
    private static final int BULK_CONTACT_PERMISSION = 709;
    private static final int BULK_PHOTO_REQUEST = 710;
    private static final int BACKGROUND = Color.rgb(10, 15, 29);
    private static final int CARD = Color.rgb(25, 36, 56);
    private static final int LIGHT = Color.rgb(233, 240, 252);
    private static final int MUTED = Color.rgb(175, 193, 218);
    private static final int ACCENT = Color.rgb(26, 104, 184);

    private WorkspaceStore store;
    private CrmWorkspace crm;
    private String pendingAttachmentJobId;
    private CrmWorkspace.Attachment pendingAttachmentExport;
    private String pendingAttachmentExportJob;
    private boolean bulkPhotoSelection;
    private LinearLayout content;
    private String currentJobId;
    private String currentCustomerId;
    private String pendingPhotoJobId;
    private String pendingInvoice;
    private boolean pendingBackup;
    private LocalDate selectedDate = LocalDate.now();
    private String scheduleMode = "Week";
    private String currentScreen = "home";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BACKGROUND);
        getWindow().setNavigationBarColor(BACKGROUND);
        if (state != null) {
            pendingInvoice = state.getString("invoice");
            pendingBackup = state.getBoolean("backup");
            pendingPhotoJobId = state.getString("photoJob");
            pendingAttachmentJobId = state.getString("attachmentJob");
            pendingAttachmentExportJob = state.getString("attachmentExportJob");
            scheduleMode = state.getString("scheduleMode", "Week");
            try { selectedDate = LocalDate.parse(
                state.getString("scheduleDate", LocalDate.now().toString())); }
            catch (Exception ignored) { selectedDate = LocalDate.now(); }
        }
        try {
            store = new WorkspaceStore(this);
            crm = new CrmWorkspace(store);
            if (state != null) {
                String page = state.getString("screen", "home");
                currentCustomerId = state.getString("customerId");
                currentJobId = state.getString("jobId");
                if ("job".equals(page) && currentJobId != null) job(currentJobId);
                else if ("customer".equals(page) && currentCustomerId != null)
                    customer(currentCustomerId);
                else if ("customers".equals(page)) customersScreen();
                else if ("schedule".equals(page)) scheduleScreen();
                else home();
            } else home();
        } catch (Exception error) {
            screen("Workspace unavailable", "Existing records were not reset.");
            label(content, "Cannot open local storage: " + error.getMessage(), 16, LIGHT);
            label(content, "Do not uninstall until a valid backup is secured.", 14, MUTED);
            button(content, "Restore from workspace ZIP backup", this::selectRestore);
            button(content, "Revert to previous validated workspace", this::revertSnapshot);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        state.putString("invoice", pendingInvoice);
        state.putBoolean("backup", pendingBackup);
        state.putString("photoJob", pendingPhotoJobId);
        state.putString("attachmentJob", pendingAttachmentJobId);
        state.putString("attachmentExportJob", pendingAttachmentExportJob);
        state.putString("scheduleMode", scheduleMode);
        state.putString("scheduleDate", selectedDate.toString());
        state.putString("screen", currentScreen);
        state.putString("customerId", currentCustomerId);
        state.putString("jobId", currentJobId);
        super.onSaveInstanceState(state);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable box(int color) {
        GradientDrawable background = new GradientDrawable();
        background.setColor(color);
        background.setCornerRadius(dp(16));
        return background;
    }

    private void screen(String title, String subtitle) {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BACKGROUND);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20), dp(22), dp(20), dp(34));
        scroll.addView(content);
        setContentView(scroll);
        if (Build.VERSION.SDK_INT >= 30) {
            scroll.setOnApplyWindowInsetsListener((view, insets) -> {
                Insets bars = insets.getInsets(
                    WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                content.setPadding(dp(20) + bars.left, dp(22) + bars.top,
                    dp(20) + bars.right, dp(34) + bars.bottom);
                return insets;
            });
            scroll.requestApplyInsets();
        }
        TextView heading = label(content, title, 27, LIGHT);
        if (Build.VERSION.SDK_INT >= 28) heading.setAccessibilityHeading(true);
        label(content, subtitle, 14, MUTED);
    }

    private TextView label(LinearLayout parent, String text, int sp, int color) {
        TextView output = new TextView(this);
        output.setText(text);
        output.setTextColor(color);
        output.setTextSize(sp);
        output.setPadding(0, dp(7), 0, dp(7));
        parent.addView(output);
        return output;
    }

    private Button button(LinearLayout parent, String title, Runnable action) {
        Button control = new Button(this);
        control.setText(title);
        control.setAllCaps(false);
        control.setTextColor(Color.WHITE);
        control.setMinHeight(dp(52));
        control.setBackgroundTintList(ColorStateList.valueOf(ACCENT));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, dp(7), 0, dp(7));
        parent.addView(control, params);
        control.setOnClickListener(view -> action.run());
        return control;
    }

    private LinearLayout card() {
        LinearLayout result = new LinearLayout(this);
        result.setOrientation(LinearLayout.VERTICAL);
        result.setPadding(dp(17), dp(15), dp(17), dp(15));
        result.setBackground(box(CARD));
        LinearLayout.LayoutParams margins = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        margins.setMargins(0, dp(10), 0, dp(10));
        content.addView(result, margins);
        return result;
    }

    private EditText field(LinearLayout parent, String label, String example) {
        TextView title = label(parent, label, 15, LIGHT);
        EditText input = new EditText(this);
        input.setId(View.generateViewId());
        title.setLabelFor(input.getId());
        input.setSingleLine(true);
        input.setHint(example);
        input.setTextColor(LIGHT);
        input.setHintTextColor(MUTED);
        input.setTextSize(17);
        input.setInputType(InputType.TYPE_CLASS_TEXT);
        input.setMinHeight(dp(56));
        parent.addView(input, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        return input;
    }

    private LinearLayout form() {
        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(dp(14), dp(10), dp(14), dp(10));
        ScrollView scroller = new ScrollView(this);
        scroller.addView(container);
        return container;
    }

    private AlertDialog dialog(String title, LinearLayout fields, Runnable onSave) {
        ScrollView wrapper = (ScrollView) fields.getParent();
        AlertDialog alert = new AlertDialog.Builder(this)
            .setTitle(title)
            .setView(wrapper)
            .setNegativeButton("Cancel", (d, w) -> {})
            .setPositiveButton("Save", null)
            .create();
        alert.setOnShowListener(d -> {
            alert.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
                try {
                    onSave.run();
                    alert.dismiss();
                } catch (Exception error) {
                    error(error);
                }
            });
        });
        alert.show();
        return alert;
    }

    private void error(Exception exception) {
        new AlertDialog.Builder(this).setTitle("Action not saved")
            .setMessage(exception.getMessage() == null ? "Unknown error" : exception.getMessage())
            .setPositiveButton("OK", (d, w) -> {})
            .show();
    }

    private void notice(String title, String message) {
        new AlertDialog.Builder(this).setTitle(title).setMessage(message)
            .setPositiveButton("OK", (d, w) -> {}).show();
    }


    /** Two rows avoid tiny taps and overlapping text at large font scaling. */
    private void navigation() {
        String[] labels = {"Home", "Customers", "Schedule", "Business"};
        Runnable[] actions = {this::home, this::customersScreen,
            this::scheduleScreen, this::businessScreen};
        for (int row=0; row<2; row++) {
            LinearLayout bar=new LinearLayout(this);
            bar.setOrientation(LinearLayout.HORIZONTAL);
            content.addView(bar,new LinearLayout.LayoutParams(-1,-2));
            for (int column=0; column<2; column++) {
                int index=row*2+column;
                Button tab=new Button(this);
                tab.setText(labels[index]);
                tab.setAllCaps(false);
                tab.setTextColor(LIGHT);
                tab.setTextSize(14);
                tab.setMinHeight(dp(52));
                tab.setContentDescription("Go to "+labels[index]);
                tab.setBackgroundTintList(ColorStateList.valueOf(CARD));
                LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);
                lp.setMargins(dp(3),dp(3),dp(3),dp(3));
                bar.addView(tab,lp);
                final Runnable action=actions[index];
                tab.setOnClickListener(v->action.run());
            }
        }
    }

    private void section(String name) {
        TextView heading = label(content, name, 20, LIGHT);
        if (Build.VERSION.SDK_INT >= 28) heading.setAccessibilityHeading(true);
    }

    private void customerRow(WorkspaceStore.Customer client) {
        try {
            CrmWorkspace.ContactPreferences preference=crm.preferences(client);
            Button entry=button(content,client.displayName()+"\n"+
                (client.phone.isEmpty()?"Open customer profile and job history":client.phone),
                ()->customer(client.id));
            entry.setBackgroundTintList(ColorStateList.valueOf(
                Color.parseColor(preference.color)));
        } catch(Exception e){error(e);}
    }

    private void jobRow(WorkspaceStore.Job job) {
        try {
            CrmWorkspace.Appointment appointment=crm.appointment(job);
            WorkspaceStore.Customer customer=null;
            for(WorkspaceStore.Customer c:store.customers())
                if(c.id.equals(job.customerId))customer=c;
            String person=customer==null?"Unknown customer":customer.displayName();
            String note=appointment.notes.isEmpty()?"":("\n"+appointment.notes);
            Button entry=button(content,job.date+" · "+appointment.start+"–"+appointment.end
                +"\n"+job.title+" · "+person+"\n"+job.status+" · $"+job.total+note,
                ()->job(job.id));
            entry.setBackgroundTintList(ColorStateList.valueOf(
                Color.parseColor(appointment.color)));
        } catch(Exception e){error(e);}
    }

    private void customersScreen() {
        currentScreen = "customers";
        currentJobId = null;
        currentCustomerId = null;
        try {
            List<WorkspaceStore.Customer> all = store.customers();
            screen("Customers", "Tap a customer to see contact details and every job");
            navigation();
            button(content, "Add customer", this::customerDialog);
            button(content, "Import selected phone contact", this::pickContact);
            EditText search = field(content, "Find a customer", "Search name, phone, email or city");
            LinearLayout results = new LinearLayout(this);
            results.setOrientation(LinearLayout.VERTICAL);
            content.addView(results);
            Runnable render = () -> {
                results.removeAllViews();
                String needle = search.getText().toString().trim().toLowerCase(java.util.Locale.ROOT);
                int count = 0;
                for (WorkspaceStore.Customer c : all) {
                    String haystack = (c.displayName() + " " + c.phone + " " + c.email
                        + " " + c.city).toLowerCase(java.util.Locale.ROOT);
                    if (!haystack.contains(needle)) continue;
                    Button entry = new Button(this);
                    entry.setAllCaps(false);
                    entry.setText(c.displayName() + "\n" + c.phone);
                    entry.setContentDescription("Open customer " + c.displayName()
                        + ", view contact information and job history");
                    entry.setTextColor(LIGHT);
                    entry.setBackgroundTintList(ColorStateList.valueOf(CARD));
                    entry.setMinHeight(dp(56));
                    LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                        -1, -2);
                    lp.setMargins(0, dp(6), 0, dp(6));
                    results.addView(entry, lp);
                    entry.setOnClickListener(v -> customer(c.id));
                    count++;
                }
                if (count == 0) label(results, "No matching customers", 16, MUTED);
            };
            render.run();
            search.addTextChangedListener(new TextWatcher() {
                public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
                public void onTextChanged(CharSequence s, int start, int before, int count) {
                    render.run();
                }
                public void afterTextChanged(Editable s) {}
            });
        } catch (Exception error) { error(error); }
    }

    /** Accessible day/week/month agenda controls. Time windows/crews remain release blockers. */
    private void scheduleScreen() {
        currentScreen = "schedule";
        currentJobId = null;
        currentCustomerId = null;
        try {
            List<WorkspaceStore.Job> jobs = store.jobs();
            LocalDate first;
            LocalDate last;
            switch (scheduleMode) {
                case "Day":
                    first = selectedDate;
                    last = selectedDate;
                    break;
                case "Month":
                    first = selectedDate.withDayOfMonth(1);
                    last = first.plusMonths(1).minusDays(1);
                    break;
                default:
                    first = selectedDate.with(
                        TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
                    last = first.plusDays(6);
            }
            screen("Schedule", scheduleMode + " · " + first + " through " + last);
            navigation();
            button(content, "Change view (currently " + scheduleMode + ")", () -> {
                String[] options = {"Day", "Week", "Month"};
                new AlertDialog.Builder(this).setTitle("Show schedule by")
                    .setSingleChoiceItems(options, java.util.Arrays.asList(options)
                        .indexOf(scheduleMode), (dialog, which) -> {
                        scheduleMode = options[which];
                        dialog.dismiss();
                        scheduleScreen();
                    }).setNegativeButton("Cancel", (d, w) -> {}).show();
            });
            button(content, "Choose a date", () -> {
                new DatePickerDialog(this, (picker, y, m, d) -> {
                    selectedDate = LocalDate.of(y, m + 1, d);
                    scheduleScreen();
                }, selectedDate.getYear(), selectedDate.getMonthValue() - 1,
                    selectedDate.getDayOfMonth()).show();
            });
            button(content, "Previous " + scheduleMode.toLowerCase(java.util.Locale.ROOT),
                () -> moveSchedule(-1));
            button(content, "Today", () -> {
                selectedDate = LocalDate.now();
                scheduleScreen();
            });
            button(content, "Next " + scheduleMode.toLowerCase(java.util.Locale.ROOT),
                () -> moveSchedule(1));
            button(content, "Schedule new job", this::chooseCustomer);
            int matches = 0;
            String day = "";
            for (WorkspaceStore.Job j : jobs) {
                LocalDate scheduled = LocalDate.parse(j.date);
                if (scheduled.isBefore(first) || scheduled.isAfter(last)) continue;
                if (!j.date.equals(day)) {
                    day = j.date;
                    section(day.equals(LocalDate.now().toString()) ? "Today · " + day : day);
                }
                jobRow(j);
                matches++;
            }
            if (matches == 0) {
                label(content, "No jobs in this " + scheduleMode.toLowerCase(
                    java.util.Locale.ROOT) + ". Use Schedule new job.", 17, MUTED);
            }
            label(content, "Day/week/month dates are available. Appointment times, "
                + "crew assignment, recurrence and conflict detection remain to be built.",
                13, MUTED);
        } catch (Exception error) { error(error); }
    }

    private void moveSchedule(int direction) {
        if (scheduleMode.equals("Day")) selectedDate = selectedDate.plusDays(direction);
        else if (scheduleMode.equals("Month"))
            selectedDate = selectedDate.plusMonths(direction);
        else selectedDate = selectedDate.plusWeeks(direction);
        scheduleScreen();
    }

    private void customer(String id) {
        currentScreen = "customer";
        currentJobId = null;
        currentCustomerId = id;
        try {
            WorkspaceStore.Customer c = null;
            for (WorkspaceStore.Customer candidate : store.customers()) {
                if (candidate.id.equals(id)) c = candidate;
            }
            if (c == null) throw new IOException("Customer not found");
            final WorkspaceStore.Customer selected = c;
            screen(c.displayName(), "Customer profile · contact · properties · job history");
            navigation();
            button(content, "Back to customers", this::customersScreen);
            section("Contact information");
            label(content, "Contact: " + c.contact, 17, LIGHT);
            label(content, "Company: " + (c.company.isEmpty() ? "Not provided" : c.company),
                16, LIGHT);
            label(content, "Phone: " + (c.phone.isEmpty() ? "Not provided" : c.phone),
                16, LIGHT);
            label(content, "Email: " + (c.email.isEmpty() ? "Not provided" : c.email),
                16, LIGHT);
            label(content, "Billing address: " + c.street + ", " + c.city + ", " + c.state
                + " " + c.zip, 16, LIGHT);
            if (!c.phone.isEmpty()) {
                button(content, "Dial " + c.phone, () -> external(Intent.ACTION_DIAL,
                    Uri.fromParts("tel", selected.phone, null)));
                button(content, "Text " + c.phone, () -> external(Intent.ACTION_SENDTO,
                    Uri.fromParts("smsto", selected.phone, null)));
            }
            if (!c.email.isEmpty()) {
                button(content, "Email " + c.email, () -> external(Intent.ACTION_SENDTO,
                    Uri.fromParts("mailto", selected.email, null)));
            }
            button(content, "Edit customer information", () -> customerDialog(selected, "", ""));
            button(content, "Schedule job for this customer", () -> jobDialog(selected));
            section("Job history");
            int count = 0;
            for (WorkspaceStore.Job j : store.jobs()) {
                if (j.customerId.equals(id)) {
                    jobRow(j);
                    count++;
                }
            }
            if (count == 0) label(content, "No jobs for this customer yet.", 16, MUTED);
        } catch (Exception error) { error(error); }
    }

    private void external(String action, Uri uri) {
        try {
            startActivity(new Intent(action, uri));
        } catch (Exception failure) {
            error(new IllegalStateException("No compatible phone, text or email app", failure));
        }
    }


    private File workspacePath() {
        return new File(getFilesDir(), "Accubook Workspace");
    }

    private void selectRestore() {
        new AlertDialog.Builder(this).setTitle("Restore workspace backup?")
            .setMessage("This replaces the current customers, jobs, and photos with the "
                + "contents of your selected ZIP. The previous workspace will be kept "
                + "locally for one rollback. Export and verify a backup first.")
            .setNegativeButton("Cancel", (d, w) -> {})
            .setPositiveButton("Select ZIP", (d, w) -> {
                Intent choose = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                choose.addCategory(Intent.CATEGORY_OPENABLE);
                choose.setType("application/zip");
                try {
                    startActivityForResult(choose, RESTORE_REQUEST);
                } catch (Exception exception) { error(exception); }
            }).show();
    }

    private void revertSnapshot() {
        if (!BackupArchive.rollback(workspacePath()).isDirectory()) {
            notice("No previous restore", "No rollback snapshot exists on this device.");
            return;
        }
        new AlertDialog.Builder(this).setTitle("Revert to previous workspace?")
            .setMessage("The current workspace will be preserved separately for recovery. "
                + "Your previous validated customer and job records will become active.")
            .setNegativeButton("Cancel", (d, w) -> {})
            .setPositiveButton("Revert", (d, w) -> {
                try {
                    BackupArchive.revertPreviousSnapshot(workspacePath());
                    store = new WorkspaceStore(this);
                    crm = new CrmWorkspace(store);
                    home();
                    notice("Previous workspace reopened", "Review records before continuing.");
                } catch (Exception failure) { error(failure); }
            }).show();
    }

    private void discardPreviousSnapshot() {
        new AlertDialog.Builder(this).setTitle("Discard previous restore snapshot?")
            .setMessage("Only do this after verifying the restored customers, jobs, photos "
                + "and exporting a new independent backup. This cannot be undone.")
            .setNegativeButton("Keep rollback", (d, w) -> {})
            .setPositiveButton("Discard", (d, w) -> {
                try {
                    store.discardRollbackSnapshot();
                    home();
                } catch (Exception failure) { error(failure); }
            }).show();
    }

    private void pickContact() {
        try {
            // User selects one phone entry. No blanket READ_CONTACTS permission.
            Intent pick = new Intent(Intent.ACTION_PICK);
            pick.setType(ContactsContract.CommonDataKinds.Phone.CONTENT_TYPE);
            startActivityForResult(pick, CONTACT_REQUEST);
        } catch (Exception failure) { error(failure); }
    }

    private void datePicker(WorkspaceStore.Job job) {
        LocalDate date = LocalDate.parse(job.date);
        new DatePickerDialog(this, (picker, year, month, day) -> {
            try {
                String iso = LocalDate.of(year, month + 1, day).toString();
                store.updateJob(job.id, iso, job.status);
                job(job.id);
            } catch (Exception failure) { error(failure); }
        }, date.getYear(), date.getMonthValue() - 1, date.getDayOfMonth()).show();
    }

    private void statusPicker(WorkspaceStore.Job job) {
        String[] statuses = {"Scheduled", "In Progress", "On Hold", "Completed", "Cancelled"};
        new AlertDialog.Builder(this).setTitle("Job status")
            .setItems(statuses, (dialog, index) -> {
                try {
                    store.updateJob(job.id, job.date, statuses[index]);
                    job(job.id);
                } catch (Exception failure) { error(failure); }
            }).setNegativeButton("Cancel", (dialog, index) -> {}).show();
    }


    private void fieldNotesDialog(WorkspaceStore.Job job) {
        try {
            LinearLayout fields = form();
            label(fields, "Field notes, crew instructions, gate/entry details", 16, LIGHT);
            EditText notes = new EditText(this);
            notes.setId(View.generateViewId());
            notes.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
            notes.setSingleLine(false);
            notes.setMinLines(6);
            notes.setTextColor(LIGHT);
            notes.setHintTextColor(MUTED);
            notes.setHint("Arrival instructions, site hazards, customer preferences...");
            notes.setText(store.fieldNotes(job));
            fields.addView(notes, new LinearLayout.LayoutParams(-1, dp(185)));
            label(fields, "These notes become part of the unencrypted workspace ZIP. "
                + "Avoid sensitive gate codes unless backups are protected.", 13, MUTED);
            dialog("Edit field notes", fields, () -> {
                try {
                    store.saveFieldNotes(job, notes.getText().toString());
                    job(job.id);
                } catch (IOException failure) {
                    throw new IllegalStateException(failure.getMessage(), failure);
                }
            });
        } catch (Exception failure) { error(failure); }
    }

    private void materialDialog(WorkspaceStore.Job job, WorkspaceStore.MaterialRequest existing) {
        LinearLayout fields = form();
        EditText description = field(fields, "Material or supply", "3-tab shingles");
        EditText quantity = field(fields, "Quantity", "2");
        quantity.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText unit = field(fields, "Unit", "bundle, roll, square...");
        if (existing != null) {
            description.setText(existing.description);
            quantity.setText(existing.quantity);
            unit.setText(existing.unit);
        }
        dialog(existing == null ? "Request material" : "Edit material", fields, () -> {
            try {
                if (existing == null) {
                    store.addMaterialRequest(job, description.getText().toString(),
                        quantity.getText().toString(), unit.getText().toString());
                } else {
                    store.updateMaterialRequest(job, existing.id,
                        description.getText().toString(), quantity.getText().toString(),
                        unit.getText().toString(), existing.status);
                }
                job(job.id);
            } catch (IOException failure) {
                throw new IllegalStateException(failure.getMessage(), failure);
            }
        });
    }

    private void materialStatusPicker(WorkspaceStore.Job job,
                                      WorkspaceStore.MaterialRequest request) {
        String[] states = {"Requested", "Ordered", "Delivered", "Used", "Cancelled"};
        new AlertDialog.Builder(this).setTitle("Material request status")
            .setItems(states, (d, which) -> {
                try {
                    store.updateMaterialRequest(job, request.id, request.description,
                        request.quantity, request.unit, states[which]);
                    job(job.id);
                } catch (Exception failure) { error(failure); }
            }).setNegativeButton("Cancel", (d, w) -> {}).show();
    }

    private void removeMaterial(WorkspaceStore.Job job, WorkspaceStore.MaterialRequest request) {
        new AlertDialog.Builder(this).setTitle("Remove material request?")
            .setMessage(request.description + " · This cannot be undone.")
            .setNegativeButton("Keep", (d, w) -> {})
            .setPositiveButton("Remove", (d, w) -> {
                try {
                    store.deleteMaterialRequest(job, request.id);
                    job(job.id);
                } catch (Exception failure) { error(failure); }
            }).show();
    }

    private void editLineDialog(WorkspaceStore.Job job, WorkspaceStore.LineItem line) {
        LinearLayout fields = form();
        EditText description = field(fields, "Description", "Work performed");
        description.setText(line.description);
        EditText quantity = field(fields, "Quantity", "1");
        quantity.setText(line.quantity);
        quantity.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText rate = field(fields, "Unit rate", "0.00");
        rate.setText(line.unitRate);
        rate.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED |
            InputType.TYPE_NUMBER_FLAG_DECIMAL);
        dialog("Edit line item", fields, () -> {
            try {
                store.updateLine(job, line.id, description.getText().toString(),
                    quantity.getText().toString(), rate.getText().toString());
                job(job.id);
            } catch (IOException exception) {
                throw new IllegalStateException(exception.getMessage(), exception);
            }
        });
    }

    private void deleteLine(WorkspaceStore.Job job, WorkspaceStore.LineItem line) {
        new AlertDialog.Builder(this).setTitle("Remove line item?")
            .setMessage(line.description + "\nThe amount will be recalculated.")
            .setNegativeButton("Keep", (d, w) -> {})
            .setPositiveButton("Remove", (d, w) -> {
                try {
                    store.deleteLine(job, line.id);
                    job(job.id);
                } catch (Exception failure) { error(failure); }
            }).show();
    }

    private void pickPhoto(WorkspaceStore.Job job) {
        pendingPhotoJobId = job.id;
        try {
            Intent pick = new Intent(Intent.ACTION_GET_CONTENT);
            pick.setType("image/*");
            pick.addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(pick, PHOTO_REQUEST);
        } catch (Exception failure) {
            pendingPhotoJobId = null;
            error(failure);
        }
    }

    private WorkspaceStore.Job jobById(String id) throws IOException {
        for (WorkspaceStore.Job candidate : store.jobs())
            if (candidate.id.equals(id)) return candidate;
        throw new IOException("Job no longer exists");
    }

    private void photoCard(WorkspaceStore.Job job, String name, int number) {
        LinearLayout panel = card();
        label(panel, "Job photo " + number, 16, LIGHT);
        try {
            File imageFile = store.photoFile(job, name);
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(imageFile.getAbsolutePath(), options);
            if (options.outWidth <= 0 || options.outHeight <= 0)
                throw new IOException("Image cannot be decoded");
            options.inJustDecodeBounds = false;
            options.inSampleSize = 1;
            while (options.outWidth / options.inSampleSize > 1200
                || options.outHeight / options.inSampleSize > 1200)
                options.inSampleSize *= 2;
            Bitmap bitmap = BitmapFactory.decodeFile(imageFile.getAbsolutePath(), options);
            if (bitmap == null) throw new IOException("Image cannot be decoded");
            ImageView preview = new ImageView(this);
            preview.setImageBitmap(bitmap);
            preview.setAdjustViewBounds(true);
            preview.setMaxHeight(dp(210));
            preview.setContentDescription("Attached photo " + number + " for " + job.title);
            panel.addView(preview, new LinearLayout.LayoutParams(-1, -2));
        } catch (Exception exception) {
            label(panel, "Photo preview unavailable: " + exception.getMessage(), 13, MUTED);
        }
        button(panel, "Remove photo " + number, () -> new AlertDialog.Builder(this)
            .setTitle("Delete this photo?")
            .setMessage("This action cannot be undone. Export a backup first.")
            .setNegativeButton("Keep", (d, w) -> {})
            .setPositiveButton("Delete", (d, w) -> {
                try {
                    store.deletePhoto(job, name);
                    job(job.id);
                } catch (Exception failure) { error(failure); }
            }).show());
    }



    /** All business settings are local. Company identity merges into every document. */
    private void businessScreen() {
        currentScreen="business";
        currentJobId=null;
        currentCustomerId=null;
        try {
            CrmWorkspace.Branding brand=crm.branding();
            screen("Business dashboard","Offline accounting overview · local only");
            navigation();
            section("Your business");
            label(content,brand.business,20,LIGHT);
            label(content,brand.address+" "+brand.phone+" "+brand.email,15,MUTED);
            button(content,"Edit company / default invoice template",this::brandingDialog);
            button(content,"Choose business logo",this::pickLogo);
            section("Payment method ledgers");
            Map<String,BigDecimal> totals=new LinkedHashMap<>();
            for(String method:CrmWorkspace.PAYMENT_METHODS)totals.put(method,BigDecimal.ZERO);
            BigDecimal draftTotal=BigDecimal.ZERO;
            BigDecimal received=BigDecimal.ZERO;
            int sent=0;
            for(WorkspaceStore.Job job:store.jobs()){
                draftTotal=draftTotal.add(new BigDecimal(job.total));
                if(crm.quote(job).sent)sent++;
                for(CrmWorkspace.Payment entry:crm.payments(job)){
                    BigDecimal value=new BigDecimal(entry.amount);
                    totals.put(entry.method,totals.get(entry.method).add(value));
                    received=received.add(value);
                }
            }
            label(content,"Draft job billing: $"+draftTotal.toPlainString(),17,LIGHT);
            label(content,"Payments recorded: $"+received.toPlainString(),17,LIGHT);
            label(content,"Unreconciled difference (drafts - receipts): $"+
                draftTotal.subtract(received).toPlainString(),16,LIGHT);
            label(content,"Quotes manually marked sent: "+sent,15,LIGHT);
            for(Map.Entry<String,BigDecimal> item:totals.entrySet())
                label(content,item.getKey()+" ledger: $"+item.getValue().toPlainString(),17,LIGHT);
            label(content,"No bank, PayPal or Cash App account connection is made. "
                +"These are manual offline ledger entries, not verified settlements.",14,MUTED);
            button(content,"Create fictional test business data",this::createTestBusiness);
            button(content,"Export full workspace backup",()->{
                pendingBackup=true;
                pendingInvoice=null;
                document("accubook-workspace.zip","application/zip");
            });
        }catch(Exception e){error(e);}
    }

    private void brandingDialog() {
        try {
            CrmWorkspace.Branding brand=crm.branding();
            LinearLayout fields=form();
            EditText business=field(fields,"Business name (required)","Example Contracting LLC");
            business.setText(brand.business);
            EditText address=field(fields,"Business address","Address");
            address.setText(brand.address);
            EditText phone=field(fields,"Business phone","Phone");
            phone.setText(brand.phone);
            EditText email=field(fields,"Business email","Email");
            email.setText(brand.email);
            EditText color=field(fields,"Brand color · #RRGGBB","#165DAB");
            color.setText(brand.accent);
            EditText terms=multiline(fields,"Default payment terms",brand.terms);
            EditText footer=multiline(fields,"Footer / business information",brand.footer);
            dialog("Default quote and invoice template",fields,()->{
                try{
                    crm.saveBranding(business.getText().toString(),address.getText().toString(),
                        phone.getText().toString(),email.getText().toString(),
                        color.getText().toString(),terms.getText().toString(),
                        footer.getText().toString());
                    businessScreen();
                }catch(IOException e){throw new IllegalStateException(e);}
            });
        }catch(Exception e){error(e);}
    }

    private EditText multiline(LinearLayout parent,String title,String value) {
        TextView heading=label(parent,title,15,LIGHT);
        EditText field=new EditText(this);
        field.setId(View.generateViewId());
        heading.setLabelFor(field.getId());
        field.setText(value==null?"":value);
        field.setTextColor(LIGHT);
        field.setHintTextColor(MUTED);
        field.setTextSize(16);
        field.setMinHeight(dp(100));
        field.setSingleLine(false);
        field.setInputType(InputType.TYPE_CLASS_TEXT |
            InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        parent.addView(field,new LinearLayout.LayoutParams(-1,-2));
        return field;
    }

    private void pickLogo() {
        Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        pick.setType("image/*");
        pick.addCategory(Intent.CATEGORY_OPENABLE);
        try {startActivityForResult(pick,LOGO_REQUEST);}
        catch(Exception e){error(e);}
    }

    private void openDocument(WorkspaceStore.Job job,boolean quote) {
        Intent intent=new Intent(this,DocumentActivity.class);
        intent.putExtra("job",job.id);
        intent.putExtra("quote",quote);
        startActivity(intent);
    }

    private void paymentDialog(WorkspaceStore.Job job) {
        LinearLayout fields=form();
        EditText date=field(fields,"Payment received date · YYYY-MM-DD","Tap calendar or type");
        date.setText(LocalDate.now().toString());
        button(fields,"Choose payment date",()->openDate(date));
        EditText amount=field(fields,"Amount received · USD","100.00");
        amount.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText reference=field(fields,"Reference / check number (optional)","Check #, transfer ID");
        EditText notes=multiline(fields,"Payment notes","");
        String[] method={CrmWorkspace.PAYMENT_METHODS[0]};
        Button choose=button(fields,"Method: "+method[0],()->{
            new AlertDialog.Builder(this).setTitle("Payment method")
                .setItems(CrmWorkspace.PAYMENT_METHODS,(d,index)->{
                    method[0]=CrmWorkspace.PAYMENT_METHODS[index];
                }).show();
        });
        // Update button caption whenever the chooser closes.
        choose.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("Payment method")
            .setItems(CrmWorkspace.PAYMENT_METHODS,(d,index)->{
                method[0]=CrmWorkspace.PAYMENT_METHODS[index];
                choose.setText("Method: "+method[0]);
            }).show());
        dialog("Record offline payment",fields,()->{
            try{
                crm.addPayment(job,date.getText().toString(),method[0],
                    amount.getText().toString(),reference.getText().toString(),
                    notes.getText().toString());
                job(job.id);
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }

    private void openDate(EditText target) {
        LocalDate initial;
        try{initial=LocalDate.parse(target.getText().toString());}
        catch(Exception ignored){initial=LocalDate.now();}
        new DatePickerDialog(this,(picker,year,month,day)->
            target.setText(LocalDate.of(year,month+1,day).toString()),
            initial.getYear(),initial.getMonthValue()-1,initial.getDayOfMonth()).show();
    }

    private void openClock(EditText target) {
        LocalTime initial;
        try{initial=LocalTime.parse(target.getText().toString());}
        catch(Exception ignored){initial=LocalTime.of(9,0);}
        new TimePickerDialog(this,(picker,hour,minute)->
            target.setText(String.format(Locale.ROOT,"%02d:%02d",hour,minute)),
            initial.getHour(),initial.getMinute(),false).show();
    }

    private void chooseJobColor(Button button,String[] chosen) {
        String[] labels={"Blue · standard","Green · active","Gold · follow-up",
            "Red · urgent","Purple · special","Slate · other"};
        new AlertDialog.Builder(this).setTitle("Color-code this job")
            .setItems(labels,(dialog,index)->{
                chosen[0]=CrmWorkspace.JOB_COLORS[index];
                button.setBackgroundTintList(ColorStateList.valueOf(Color.parseColor(chosen[0])));
                button.setText("Job color: "+labels[index]);
            }).show();
    }

    private void scheduleEditor(WorkspaceStore.Job job) {
        try {
            CrmWorkspace.Appointment old=crm.appointment(job);
            LinearLayout fields=form();
            EditText date=field(fields,"Appointment date · YYYY-MM-DD","YYYY-MM-DD");
            date.setText(job.date);
            button(fields,"Select date in calendar",()->openDate(date));
            EditText start=field(fields,"Start time · HH:mm","09:00");
            start.setText(old.start);
            button(fields,"Choose start time on clock",()->openClock(start));
            EditText end=field(fields,"End time · HH:mm","10:00");
            end.setText(old.end);
            button(fields,"Choose end time on clock",()->openClock(end));
            String[] tint={old.color};
            Button colorButton=button(fields,"Choose job color",()->{});
            colorButton.setBackgroundTintList(ColorStateList.valueOf(Color.parseColor(tint[0])));
            colorButton.setOnClickListener(v->chooseJobColor(colorButton,tint));
            EditText note=multiline(fields,"Daybook appointment note",old.notes);
            dialog("Reschedule job / edit daybook",fields,()->{
                LocalTime from=LocalTime.parse(start.getText().toString());
                LocalTime to=LocalTime.parse(end.getText().toString());
                if(!to.isAfter(from))throw new IllegalArgumentException("End time must follow start time");
                try{
                    // Date is canonical in jobs.csv; appointment details are a separate
                    // additive file. This multi-file edit needs journaled recovery later.
                    WorkspaceStore.Job changed=store.updateJob(job.id,date.getText().toString(),
                        job.status);
                    crm.saveAppointment(changed,start.getText().toString(),end.getText().toString(),
                        tint[0],note.getText().toString());
                    job(changed.id);
                }catch(IOException e){throw new IllegalStateException(e);}
            });
        }catch(Exception e){error(e);}
    }

    private void pickAttachments(WorkspaceStore.Job job,boolean imagesOnly) {
        pendingAttachmentJobId=job.id;
        bulkPhotoSelection=imagesOnly;
        Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
        pick.setType(imagesOnly?"image/*":"*/*");
        pick.addCategory(Intent.CATEGORY_OPENABLE);
        pick.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);
        try{startActivityForResult(pick,imagesOnly?BULK_PHOTO_REQUEST:ATTACHMENT_REQUEST);}
        catch(Exception e){pendingAttachmentJobId=null;error(e);}
    }

    private void saveSelectedAttachments(Intent data,boolean photos) {
        String jobId=pendingAttachmentJobId;
        pendingAttachmentJobId=null;
        if(jobId==null)return;
        try{
            WorkspaceStore.Job selected=jobById(jobId);
            ArrayList<Uri> uris=new ArrayList<>();
            if(data.getClipData()!=null){
                ClipData clip=data.getClipData();
                for(int i=0;i<clip.getItemCount();i++)uris.add(clip.getItemAt(i).getUri());
            }else if(data.getData()!=null)uris.add(data.getData());
            if(uris.size()>40)throw new IOException("Choose no more than 40 files in one batch");
            int imported=0;
            for(Uri uri:uris){
                if(photos){
                    try(InputStream stream=getContentResolver().openInputStream(uri)){
                        store.addPhoto(selected,stream);
                    }
                } else {
                    String name="Attachment";
                    try(Cursor cursor=getContentResolver().query(uri,
                        new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){
                        if(cursor!=null&&cursor.moveToFirst())name=cursor.getString(0);
                    }
                    if(name==null||name.isEmpty())name="Attachment";
                    String mime=getContentResolver().getType(uri);
                    try(InputStream stream=getContentResolver().openInputStream(uri)){
                        crm.importAttachment(selected,stream,name,mime==null?"":mime);
                    }
                }
                imported++;
            }
            job(jobId);
            notice("Import completed",imported+" files saved privately with this job.");
        }catch(Exception e){error(e);}
    }

    private void exportAttachment(WorkspaceStore.Job job,CrmWorkspace.Attachment attachment) {
        pendingAttachmentExport=attachment;
        pendingAttachmentExportJob=job.id;
        document(attachment.name,attachment.mime);
    }

    private void attachmentList(WorkspaceStore.Job job) throws IOException {
        section("Job files and attachments");
        button(content,"Attach files (select multiple, any format)",()->pickAttachments(job,false));
        button(content,"Import multiple photographs",()->pickAttachments(job,true));
        List<CrmWorkspace.Attachment> files=crm.attachments(job);
        if(files.isEmpty())label(content,"No files attached yet.",15,MUTED);
        for(CrmWorkspace.Attachment file:files){
            LinearLayout row=card();
            label(row,file.name+" · "+file.mime+" · "+file.bytes+" bytes",15,LIGHT);
            button(row,"Save a copy of "+file.name,()->exportAttachment(job,file));
            button(row,"Remove "+file.name,()->new AlertDialog.Builder(this)
                .setTitle("Remove attached file?")
                .setMessage(file.name+" will be deleted from this job.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton("Delete",(d,w)->{
                    try{crm.deleteAttachment(job,file);job(job.id);}
                    catch(Exception e){error(e);}
                }).show());
        }
    }

    private void createTestBusiness() {
        new AlertDialog.Builder(this).setTitle("Load fictional test company?")
            .setMessage("Creates a fictional example contracting business, three demo customers, "
                +"three jobs, appointment times, draft charges and sample payment-method entries. "
                +"Existing records are not replaced. Never use this data for real accounting.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Create sample",(d,w)->{
                try {
                    crm.saveBranding("Evergreen Exterior Services · DEMO",
                        "20 Sample Way, Boston MA 02108","555-0120",
                        "office@example.invalid","#165DAB",
                        "DEMO ONLY: payment due upon completion.",
                        "This is fictional test data, not a financial document.");
                    String[] customers={"Jordan Example","Avery Sample","Taylor Demo"};
                    String[] titles={"Roof inspection","Gutter clean and repair","Siding estimate"};
                    String[] methods={"Cash","Check","PayPal"};
                    for(int i=0;i<3;i++){
                        WorkspaceStore.Customer c=store.addCustomer("",
                            customers[i],"555-01"+(20+i),"client"+i+"@example.invalid",
                            (i+20)+" Sample Street","Boston","MA","02108");
                        WorkspaceStore.Job j=store.addJob(c,"DEMO - "+titles[i],
                            c.street,c.city,c.state,c.zip,
                            LocalDate.now().plusDays(i+1).toString());
                        crm.saveAppointment(j,String.format(Locale.ROOT,"%02d:00",9+i),
                            String.format(Locale.ROOT,"%02d:00",10+i),
                            CrmWorkspace.JOB_COLORS[i],"DEMO daybook note "+(i+1));
                        crm.savePreferences(c,true,i==1,true,CrmWorkspace.JOB_COLORS[i]);
                        store.addLine(j,"DEMO labor","2","95.00");
                        store.addLine(j,"DEMO materials","1","45.00");
                        store.saveFieldNotes(j,"DEMO ONLY: confirm site details, take "
                            +"photographs and issue a quote before work.");
                        crm.setQuoteSent(j,i==2,"Fictional sample status");
                        if(i<2)crm.addPayment(j,LocalDate.now().toString(),methods[i],
                            "50.00","DEMO","Fictional deposit");
                    }
                    businessScreen();
                    notice("Demo company created","Three fictional customers, jobs, schedules "
                        +"and sample financial records are now available.");
                }catch(Exception e){error(e);}
            }).show();
    }

    /** Explicit demo seeding: no real contacts, no network, no silent first-run writes. */
    private void createDemoWorkspace() {
        new AlertDialog.Builder(this)
            .setTitle("Create a sample customer and job?")
            .setMessage("Adds a clearly labeled fictional customer, example gutter-cleaning "
                + "job, sample invoice line, and field note. Existing records stay unchanged. "
                + "Use only for testing; the example is not a real invoice.")
            .setNegativeButton("Cancel", (dialog, which) -> {})
            .setPositiveButton("Create sample", (dialog, which) -> {
                try {
                    WorkspaceStore.Customer example = store.addCustomer(
                        "Accubook Demo Property", "Sample Customer",
                        "555-0100", "sample@example.invalid", "10 Example Road",
                        "Boston", "MA", "02108");
                    WorkspaceStore.Job exampleJob = store.addJob(example,
                        "DEMO - Gutter inspection and cleaning", "10 Example Road",
                        "Boston", "MA", "02108", LocalDate.now().plusDays(1).toString());
                    store.addLine(exampleJob, "Demo labor - gutter cleaning", "2", "85.00");
                    store.addLine(exampleJob, "Demo material - gutter sealant", "1", "18.50");
                    store.saveFieldNotes(exampleJob, "DEMO ONLY: inspect gutters, document "
                        + "before and after photos, and review materials.");
                    customer(example.id);
                    notice("Sample ready", "Tap the sample job under Job history. "
                        + "Reschedule it, attach a test photo, and inspect the draft invoice.");
                } catch (Exception failure) { error(failure); }
            }).show();
    }

    private void home() {
        currentScreen = "home";
        currentJobId = null;
        currentCustomerId = null;
        try {
            List<WorkspaceStore.Customer> customers = store.customers();
            List<WorkspaceStore.Job> jobs = store.jobs();
            screen("Accubook", "Your offline field service workspace");
            navigation();
            section("Overview");
            label(content, customers.size() + " customers · " + jobs.size() + " jobs", 18, LIGHT);
            button(content, "New customer", this::customerDialog);
            button(content, "Try with a sample customer and job", this::createDemoWorkspace);
            button(content, "Schedule job", this::chooseCustomer);
            button(content, "Import phone contact", this::pickContact);
            button(content, "Export workspace ZIP backup", () -> {
                pendingBackup = true;
                pendingInvoice = null;
                document("accubook-workspace.zip", "application/zip");
            });
            button(content, "Restore workspace from ZIP", this::selectRestore);
            if (store.hasRollbackSnapshot()) {
                button(content, "Revert to previous workspace", this::revertSnapshot);
                button(content, "Discard verified rollback snapshot",
                    this::discardPreviousSnapshot);
            }
            section("Upcoming and recent work");
            int count = 0;
            for (WorkspaceStore.Job j : jobs) {
                if (j.date.compareTo(LocalDate.now().toString()) >= 0 && count < 8) {
                    jobRow(j);
                    count++;
                }
            }
            if (count == 0) label(content, "No upcoming jobs. Use Schedule to add work.", 16, MUTED);
            section("Customers");
            for (int i = 0; i < Math.min(5, customers.size()); i++)
                customerRow(customers.get(i));
            if (customers.isEmpty()) label(content, "No customers yet.", 16, MUTED);
            button(content, "Browse all customers", this::customersScreen);
            label(content, "Stored only on this device. Back up regularly. Uninstall deletes private data.",
                13, MUTED);
        } catch (Exception failure) { error(failure); }
    }


    private void customerDialog() { customerDialog(null, "", ""); }

    private void customerDialog(WorkspaceStore.Customer existing, String selectedName,
                                String selectedPhone) {
        LinearLayout fields = form();
        EditText company = field(fields, "Company (optional)", "Business name");
        EditText contact = field(fields, "Contact name (required)", "First and last name");
        EditText phone = field(fields, "Phone", "+1...");
        phone.setInputType(InputType.TYPE_CLASS_PHONE);
        EditText email = field(fields, "Email", "name@example.com");
        email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText street = field(fields, "Billing street", "123 Main St");
        EditText city = field(fields, "City", "Boston");
        EditText state = field(fields, "State", "MA");
        EditText zip = field(fields, "Postal code", "02108");
        if (existing == null) {
            contact.setText(selectedName);
            phone.setText(selectedPhone);
        } else {
            company.setText(existing.company);
            contact.setText(existing.contact);
            phone.setText(existing.phone);
            email.setText(existing.email);
            street.setText(existing.street);
            city.setText(existing.city);
            state.setText(existing.state);
            zip.setText(existing.zip);
        }
        dialog(existing == null ? "New customer" : "Edit customer", fields, () -> {
            try {
                WorkspaceStore.Customer saved = existing == null
                    ? store.addCustomer(company.getText().toString(), contact.getText().toString(),
                        phone.getText().toString(), email.getText().toString(),
                        street.getText().toString(), city.getText().toString(),
                        state.getText().toString(), zip.getText().toString())
                    : store.updateCustomer(existing.id, company.getText().toString(),
                        contact.getText().toString(), phone.getText().toString(),
                        email.getText().toString(), street.getText().toString(),
                        city.getText().toString(), state.getText().toString(),
                        zip.getText().toString());
                customer(saved.id);
            } catch (IOException exception) {
                throw new IllegalStateException(exception.getMessage(), exception);
            }
        });
    }

    private void chooseCustomer() {
        try {
            List<WorkspaceStore.Customer> customers = store.customers();
            if (customers.isEmpty()) {
                notice("Customer required", "Create a customer before scheduling a job.");
                return;
            }
            String[] names = new String[customers.size()];
            for (int i=0; i<customers.size(); i++) names[i] = customers.get(i).displayName();
            new AlertDialog.Builder(this).setTitle("Select a customer")
                .setItems(names, (dialog, index) -> jobDialog(customers.get(index)))
                .setNegativeButton("Cancel", (d, w) -> {})
                .show();
        } catch (Exception exception) { error(exception); }
    }

    private void jobDialog(WorkspaceStore.Customer customer) {
        LinearLayout fields = form();
        label(fields, "For " + customer.displayName(), 14, MUTED);
        EditText title = field(fields, "Job title (required)", "Gutter cleaning");
        EditText street = field(fields, "Site street", "123 Main St");
        EditText city = field(fields, "Site city", "Boston");
        EditText state = field(fields, "Site state", "MA");
        EditText zip = field(fields, "Site postal code", "02108");
        EditText date = field(fields, "Scheduled date · YYYY-MM-DD", "YYYY-MM-DD");
        date.setText(LocalDate.now().toString());
        dialog("New job", fields, () -> {
            try {
                WorkspaceStore.Job newJob = store.addJob(
                    customer, title.getText().toString(), street.getText().toString(),
                    city.getText().toString(), state.getText().toString(),
                    zip.getText().toString(), date.getText().toString());
                job(newJob.id);
            } catch (IOException exception) {
                throw new IllegalStateException(exception.getMessage(), exception);
            }
        });
    }


    private void job(String id) {
        currentScreen = "job";
        currentJobId = id;
        try {
            WorkspaceStore.Job selected = jobById(id);
            WorkspaceStore.Customer customer = null;
            for (WorkspaceStore.Customer candidate : store.customers()) {
                if (candidate.id.equals(selected.customerId)) customer = candidate;
            }
            if (customer == null) throw new IOException("Customer no longer exists");
            final WorkspaceStore.Job work = selected;
            final WorkspaceStore.Customer client = customer;
            screen(work.title, client.displayName() + " · " + work.date + " · " + work.status);
            navigation();
            button(content, "Customer: " + client.displayName(), () -> customer(client.id));
            section("Job details");
            label(content, "Scheduled: " + work.date, 17, LIGHT);
            label(content, "Status: " + work.status, 17, LIGHT);
            label(content, "Site: " + work.street + ", " + work.city + ", " + work.state
                + " " + work.zip, 16, LIGHT);
            button(content, "Reschedule date", () -> datePicker(work));
            button(content, "Change job status", () -> statusPicker(work));
            section("Field notes and site instructions");
            String notes = store.fieldNotes(work);
            label(content, notes.isEmpty() ? "No field notes yet."
                : (notes.length() > 800 ? notes.substring(0, 800) + "…" : notes),
                15, MUTED);
            button(content, "Edit field notes", () -> fieldNotesDialog(work));
            section("Material requests");
            button(content, "Request materials", () -> materialDialog(work, null));
            for (WorkspaceStore.MaterialRequest request : store.materialRequests(work)) {
                LinearLayout entry = card();
                label(entry, request.description + " · " + request.quantity + " "
                    + request.unit + " · " + request.status, 16, LIGHT);
                button(entry, "Edit " + request.description,
                    () -> materialDialog(work, request));
                button(entry, "Update material status", () -> materialStatusPicker(work, request));
                button(entry, "Remove request", () -> removeMaterial(work, request));
            }
            section("Invoice draft");
            label(content, "Total: $" + work.total, 22, LIGHT);
            button(content, "Add labor, material or discount", () -> lineDialog(work));
            button(content, "Export draft HTML invoice", () -> {
                try {
                    pendingInvoice = InvoiceHtml.render(client, work, store.items(work));
                    pendingBackup = false;
                    document("invoice-" + work.id + ".html", "text/html");
                } catch (Exception failure) { error(failure); }
            });
            for (WorkspaceStore.LineItem item : store.items(work)) {
                LinearLayout row = card();
                label(row, item.description, 17, LIGHT);
                label(row, item.quantity + " × $" + item.unitRate + " = $" + item.amount, 14, MUTED);
                button(row, "Edit " + item.description, () -> editLineDialog(work, item));
                button(row, "Remove " + item.description, () -> deleteLine(work, item));
            }
            section("Job photos");
            button(content, "Add photo from device", () -> pickPhoto(work));
            int index = 0;
            for (String name : store.photos(work)) photoCard(work, name, ++index);
            if (index == 0) label(content, "No photos attached to this job.", 15, MUTED);
            label(content, "Draft invoice only. Payment, tax and appointment-time accounting "
                + "are not configured.", 13, MUTED);
        } catch (Exception failure) { error(failure); }
    }

    private void lineDialog(WorkspaceStore.Job job) {
        LinearLayout fields = form();
        EditText description = field(fields, "Description (required)", "4-inch gutter cleanout");
        EditText quantity = field(fields, "Quantity", "1");
        quantity.setText("1");
        quantity.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText rate = field(fields, "Unit rate · negative only for discount", "85.00");
        rate.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED |
            InputType.TYPE_NUMBER_FLAG_DECIMAL);
        dialog("New line item", fields, () -> {
            try {
                store.addLine(job, description.getText().toString(),
                    quantity.getText().toString(), rate.getText().toString());
                job(job.id);
            } catch (IOException exception) {
                throw new IllegalStateException(exception.getMessage(), exception);
            }
        });
    }

    private void document(String name, String mime) {
        Intent destination = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        destination.addCategory(Intent.CATEGORY_OPENABLE);
        destination.setType(mime);
        destination.putExtra(Intent.EXTRA_TITLE, name);
        try {
            startActivityForResult(destination, EXPORT_REQUEST);
        } catch (Exception exception) {
            pendingBackup = false;
            pendingInvoice = null;
            error(exception);
        }
    }


    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == RESTORE_REQUEST) {
            if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
            try (InputStream zip = getContentResolver().openInputStream(data.getData())) {
                if (store == null) BackupArchive.restore(workspacePath(), zip);
                else store.restoreBackup(zip);
                store = new WorkspaceStore(this);
                crm = new CrmWorkspace(store);
                home();
                notice("Restore completed", "Review all records and photo evidence. "
                    + "The previous workspace is retained until you discard it.");
            } catch (Exception failure) {
                error(failure);
            }
            return;
        }
        if (requestCode == CONTACT_REQUEST) {
            if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
            try (Cursor cursor = getContentResolver().query(data.getData(),
                new String[]{ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER}, null, null, null)) {
                if (cursor == null || !cursor.moveToFirst()) {
                    throw new IOException("Selected contact cannot be read");
                }
                // Scoped result URI, no full address book access.
                customerDialog(null, cursor.getString(0), cursor.getString(1));
            } catch (Exception failure) { error(failure); }
            return;
        }
        if (requestCode == PHOTO_REQUEST) {
            String jobId = pendingPhotoJobId;
            pendingPhotoJobId = null;
            if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
            if (jobId == null) return;
            try (InputStream input = getContentResolver().openInputStream(data.getData())) {
                WorkspaceStore.Job work = jobById(jobId);
                store.addPhoto(work, input);
                job(jobId);
            } catch (Exception failure) { error(failure); }
            return;
        }
        if (requestCode != EXPORT_REQUEST) return;
        try {
            if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
            Uri uri = data.getData();
            ContentResolver resolver = getContentResolver();
            try (OutputStream output = resolver.openOutputStream(uri, "wt")) {
                if (output == null) throw new IOException("Cannot open selected destination");
                if (pendingBackup) {
                    store.exportBackup(output);
                } else if (pendingInvoice != null) {
                    output.write(pendingInvoice.getBytes(StandardCharsets.UTF_8));
                    output.flush();
                } else throw new IOException("Export request expired, try again");
            }
            notice("Export complete", "Saved to the selected location. Verify the file exists.");
        } catch (Exception exception) {
            error(exception);
        } finally {
            pendingBackup = false;
            pendingInvoice = null;
        }
    }


    @Override
    public void onBackPressed() {
        if (currentJobId != null) {
            if (currentCustomerId != null) customer(currentCustomerId);
            else scheduleScreen();
        } else if (currentCustomerId != null) customersScreen();
        else super.onBackPressed();
    }


}
