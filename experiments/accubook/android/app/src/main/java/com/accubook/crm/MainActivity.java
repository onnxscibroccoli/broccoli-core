package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
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
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;

/** Offline debug UI. No remote permissions, services or privileged APIs. */
public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 702;
    private static final int BACKGROUND = Color.rgb(10, 15, 29);
    private static final int CARD = Color.rgb(25, 36, 56);
    private static final int LIGHT = Color.rgb(233, 240, 252);
    private static final int MUTED = Color.rgb(175, 193, 218);
    private static final int ACCENT = Color.rgb(26, 104, 184);

    private WorkspaceStore store;
    private LinearLayout content;
    private String currentJobId;
    private String pendingInvoice;
    private boolean pendingBackup;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BACKGROUND);
        getWindow().setNavigationBarColor(BACKGROUND);
        try {
            store = new WorkspaceStore(this);
            home();
        } catch (Exception error) {
            screen("Workspace unavailable", "Existing records were not reset.");
            label(content, "Cannot open local storage: " + error.getMessage(), 16, LIGHT);
            label(content, "Do not uninstall until a valid backup is secured.", 14, MUTED);
        }
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
        label(content, title, 27, LIGHT);
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
        label(parent, label, 15, LIGHT);
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint(example);
        input.setTextColor(LIGHT);
        input.setHintTextColor(MUTED);
        input.setTextSize(17);
        input.setInputType(InputType.TYPE_CLASS_TEXT);
        parent.addView(input, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(53)));
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

    private void home() {
        currentJobId = null;
        try {
            List<WorkspaceStore.Customer> customers = store.customers();
            List<WorkspaceStore.Job> jobs = store.jobs();
            screen("Accubook", "Field service workspace · Offline development build");
            label(content, "Your records remain on this device until you export them.", 14, MUTED);
            button(content, "Add customer", this::customerDialog);
            button(content, "Schedule job", this::chooseCustomer);
            button(content, "Export workspace ZIP backup", () -> {
                pendingBackup = true;
                pendingInvoice = null;
                document("accubook-workspace.zip", "application/zip");
            });
            label(content, "Customers (" + customers.size() + ")", 20, LIGHT);
            for (WorkspaceStore.Customer customer : customers) {
                LinearLayout row = card();
                label(row, customer.displayName(), 17, LIGHT);
                label(row, customer.city + " " + customer.state, 13, MUTED);
            }
            label(content, "Scheduled work (" + jobs.size() + ")", 20, LIGHT);
            for (WorkspaceStore.Job job : jobs) {
                LinearLayout row = card();
                label(row, job.title, 18, LIGHT);
                label(row, job.date + " · " + job.status + " · $" + job.total, 14, MUTED);
                row.setContentDescription("Open job: " + job.title + ", " + job.date);
                row.setClickable(true);
                row.setFocusable(true);
                row.setOnClickListener(view -> job(job.id));
            }
            label(content, "No account, subscription, internet or privileged access required.", 13, MUTED);
        } catch (Exception failure) {
            error(failure);
        }
    }

    private void customerDialog() {
        LinearLayout fields = form();
        EditText company = field(fields, "Company (optional)", "Example Trading Co.");
        EditText contact = field(fields, "Contact name (required)", "First and last name");
        EditText phone = field(fields, "Phone", "+1...");
        phone.setInputType(InputType.TYPE_CLASS_PHONE);
        EditText email = field(fields, "Email", "name@example.com");
        email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText street = field(fields, "Billing street", "123 Main St");
        EditText city = field(fields, "City", "Boston");
        EditText state = field(fields, "State", "MA");
        EditText zip = field(fields, "Postal code", "02108");
        dialog("New customer", fields, () -> {
            try {
                store.addCustomer(company.getText().toString(), contact.getText().toString(),
                    phone.getText().toString(), email.getText().toString(),
                    street.getText().toString(), city.getText().toString(),
                    state.getText().toString(), zip.getText().toString());
                home();
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
        currentJobId = id;
        try {
            WorkspaceStore.Job selected = null;
            for (WorkspaceStore.Job candidate : store.jobs()) {
                if (candidate.id.equals(id)) selected = candidate;
            }
            if (selected == null) throw new IOException("Job no longer exists");
            WorkspaceStore.Customer customer = null;
            for (WorkspaceStore.Customer candidate : store.customers()) {
                if (candidate.id.equals(selected.customerId)) customer = candidate;
            }
            if (customer == null) throw new IOException("Customer no longer exists");
            final WorkspaceStore.Job job = selected;
            final WorkspaceStore.Customer client = customer;
            screen(job.title, client.displayName() + " · " + job.date + " · " + job.status);
            button(content, "Back to all jobs", this::home);
            label(content, "Site: " + job.street + ", " + job.city + ", " + job.state + " " + job.zip,
                16, LIGHT);
            label(content, "Total: $" + job.total, 22, LIGHT);
            button(content, "Add labor / material / discount line", () -> lineDialog(job));
            button(content, "Export draft HTML invoice", () -> {
                try {
                    pendingInvoice = InvoiceHtml.render(client, job, store.items(job));
                    pendingBackup = false;
                    document("invoice-" + job.id + ".html", "text/html");
                } catch (Exception failure) { error(failure); }
            });
            label(content, "Line items", 20, LIGHT);
            for (WorkspaceStore.LineItem item : store.items(job)) {
                LinearLayout row = card();
                label(row, item.description, 17, LIGHT);
                label(row, item.quantity + " × $" + item.unitRate + " = $" + item.amount, 14, MUTED);
            }
            label(content, "This is a draft invoice, not proof of payment.", 13, MUTED);
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
                } else {
                    throw new IOException("Export request expired, try again");
                }
            }
            notice("Export complete", "Saved to the location you selected. Verify the file exists.");
        } catch (Exception exception) {
            error(exception);
        } finally {
            pendingBackup = false;
            pendingInvoice = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (currentJobId != null) home();
        else super.onBackPressed();
    }
}
