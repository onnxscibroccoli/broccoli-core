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
import java.util.Set;
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
    private boolean pendingImportAllContacts=false;
    private static final int BACKGROUND = Color.rgb(13, 22, 38);
    private static final int CARD = Color.rgb(30, 50, 73);
    private static final int LIGHT = Color.rgb(246, 250, 255);
    private static final int MUTED = Color.rgb(201, 216, 232);
    private static final int ACCENT = Color.rgb(23, 126, 198);

    private WorkspaceStore store;
    private CrmWorkspace crm;
    private String pendingAttachmentJobId;
    private CrmWorkspace.Attachment pendingAttachmentExport;
    private String pendingAttachmentExportId;
    private String pendingAttachmentExportJob;
    private boolean bulkPhotoSelection;
    private int currentPhotoPage=0;
    private LinearLayout content;
    private String currentJobId;
    private String currentCustomerId;
    private String pendingPhotoJobId;
    private String pendingInvoice;
    private boolean pendingBackup;
    private LocalDate selectedDate = LocalDate.now();
    private String scheduleMode = "Week";
    private String currentScreen = "home";
    private String currentJobSection = "overview";
    private int lookupRequestSerial=0;
    private static final int UNLOCK_REQUEST=853;
    private static final int ROUTE_LOCATION_PERMISSION=855;
    private static final int ROUTE_EXPORT_REQUEST=856;
    private static final int REPORT_EXPORT_REQUEST=857;
    private static final int ENCRYPTED_BACKUP_EXPORT=858;
    private static final int ENCRYPTED_BACKUP_IMPORT=859;
    private static final int CALENDAR_PERMISSIONS=860;
    private static final int SUPPLIER_CSV_REQUEST=861;
    private static final int PICKUP_NOTIFY_PERMISSION=862;
    private static final int SERVICE_SLIP_PDF_REQUEST=863;
    private static final int BUSINESS_SETUP_REQUEST=864;
    private String pendingPickupJobId;
    private long pendingPickupWhen;
    private boolean lockRequestInProgress=false;
    private boolean unlocked=false;
    private long lastHiddenAt=0;
    private Bundle restoreAfterUnlock;
    private String routeJobId;
    private String pendingRouteExportId;
    private boolean[] pendingReportSections;
    private String[] pendingReportMethods;
    private String[] pendingReportCategories;
    private boolean pendingReportPdf;
    private android.location.LocationManager locationManager;
    private android.location.LocationListener routeListener;
    private char[] pendingBackupPassword;


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
            pendingAttachmentExportId = state.getString("attachmentExportId");
            pendingReportSections=state.getBooleanArray("reportSections");
            pendingReportMethods=state.getStringArray("reportMethods");
            pendingReportCategories=state.getStringArray("reportCategories");
            pendingReportPdf=state.getBoolean("reportPdf",false);
            currentJobSection=state.getString("jobSection","overview");
            currentPhotoPage=state.getInt("photoPage",0);
            pendingRouteExportId=state.getString("routeExportId");
            pendingPickupJobId=state.getString("pickupJobId");
            pendingPickupWhen=state.getLong("pickupWhen",0);
            scheduleMode = state.getString("scheduleMode", "Week");
            try { selectedDate = LocalDate.parse(
                state.getString("scheduleDate", LocalDate.now().toString())); }
            catch (Exception ignored) { selectedDate = LocalDate.now(); }
        }
        if(UnlockActivity.isEnabled(this)){
            getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
            restoreAfterUnlock=state;
            lockedScreen();
            requestUnlock();
        }else{
            unlocked=true;
            initializeWorkspace(state);
        }
    }

    private void initializeWorkspace(Bundle state) {
            try {
                store = new WorkspaceStore(this);
                crm = new CrmWorkspace(store);
                // Only an empty, not-yet-configured workspace gets the initial setup.
                // Existing customer/job records are never modified during onboarding.
                boolean firstRunSetup=state==null && !BusinessSetupStore.exists(this)
                    && store.customers().isEmpty() && store.jobs().isEmpty();
                if (state != null) {
                    String page = state.getString("screen", "home");
                    currentCustomerId = state.getString("customerId");
                    currentJobId = state.getString("jobId");
                    if ("job".equals(page) && currentJobId != null) job(currentJobId);
                    else if ("customer".equals(page) && currentCustomerId != null)
                        customer(currentCustomerId);
                    else if ("customers".equals(page)) customersScreen();
                    else if ("schedule".equals(page)) scheduleScreen();
                else if("calendar".equals(page))calendarScreen();
                else if("catalog".equals(page))catalogScreen();
                else if("settings".equals(page))settingsScreen();
                else if("help".equals(page))helpScreen();
                else if("lookup".equals(page))universalSearchScreen();
                else if("service_due".equals(page))serviceDueScreen();
                else if("contacts".equals(page))contactsScreen();
                else if("contact".equals(page))contactsScreen();
                else if("jobs".equals(page))jobsScreen();
                else if("job_template".equals(page))masterJobTemplateScreen();
                    else home();
                } else home();
                if(firstRunSetup)openBusinessSetup();
            } catch (Exception error) {
                screen("Workspace unavailable", "Existing records were not reset.");
                label(content, "Cannot open local storage: " + error.getMessage(), 16, LIGHT);
                label(content, "Do not uninstall until a valid backup is secured.", 14, MUTED);
                button(content, "Restore from workspace ZIP backup", this::selectRestore);
                button(content, "Revert to previous validated workspace", this::revertSnapshot);
            }
    }
    private void openBusinessSetup(){
        startActivityForResult(new Intent(this,BusinessSetupActivity.class),BUSINESS_SETUP_REQUEST);
    }
    private void lockedScreen(){
        // Ensure sensitive customer widgets are not drawn while OS authentication runs.
        LinearLayout cover=new LinearLayout(this);
        cover.setOrientation(LinearLayout.VERTICAL);
        cover.setPadding(dp(24),dp(35),dp(24),dp(24));
        cover.setBackgroundColor(BACKGROUND);
        TextView heading=label(cover,"Accubook locked",27,LIGHT);
        label(cover,"Unlock with your fingerprint or device PIN.",17,MUTED);
        button(cover,"Unlock now",this::requestUnlock);
        setContentView(cover);
    }
    private void requestUnlock(){
        if(lockRequestInProgress)return;
        if(!UnlockActivity.isEnabled(this)){
            unlocked=true;
            initializeWorkspace(restoreAfterUnlock);
            return;
        }
        lockRequestInProgress=true;
        Intent intent=new Intent(this,UnlockActivity.class);
        startActivityForResult(intent,UNLOCK_REQUEST);
    }
    @Override protected void onStop(){
        if(routeListener!=null)stopRoute(); // Foreground-only: never track in background.

        if(UnlockActivity.isEnabled(this))lastHiddenAt=android.os.SystemClock.elapsedRealtime();
        super.onStop();
    }
    @Override protected void onStart(){
        super.onStart();
        if(store!=null&&UnlockActivity.isEnabled(this)&&!lockRequestInProgress&&
            lastHiddenAt>0&&android.os.SystemClock.elapsedRealtime()-lastHiddenAt>30000) {
            unlocked=false;
            lockedScreen();
            requestUnlock();
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        state.putString("invoice", pendingInvoice);
        state.putBoolean("backup", pendingBackup);
        state.putString("photoJob", pendingPhotoJobId);
        state.putString("attachmentJob", pendingAttachmentJobId);
        state.putString("attachmentExportJob", pendingAttachmentExportJob);
        state.putString("attachmentExportId", pendingAttachmentExportId);
        state.putBooleanArray("reportSections",pendingReportSections);
        state.putStringArray("reportMethods",pendingReportMethods);
        state.putStringArray("reportCategories",pendingReportCategories);
        state.putBoolean("reportPdf",pendingReportPdf);
        state.putString("jobSection",currentJobSection);
        state.putInt("photoPage",currentPhotoPage);
        state.putString("routeExportId",pendingRouteExportId);
        state.putString("pickupJobId",pendingPickupJobId);
        state.putLong("pickupWhen",pendingPickupWhen);
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
        background.setCornerRadius(dp(26));
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
        control.setBackground(new android.graphics.drawable.RippleDrawable(
            ColorStateList.valueOf(0x44ffffff),box(ACCENT),null));
        control.setElevation(dp(2));
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
        result.setElevation(dp(5));
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


    /** Six clear workspaces; two columns preserve 48dp touch targets at large text. */
    private void navigation() {
        String[] labels={"Home","Jobs","Calendar","Contacts","Customers","Business"};
        Runnable[] actions={this::home,this::jobsScreen,this::calendarScreen,
            this::contactsScreen,this::customersScreen,this::businessScreen};
        for(int row=0;row<3;row++){
            LinearLayout bar=new LinearLayout(this);
            bar.setOrientation(LinearLayout.HORIZONTAL);
            content.addView(bar,new LinearLayout.LayoutParams(-1,-2));
            for(int col=0;col<2;col++){
                int index=row*2+col;
                Button tab=new Button(this);
                tab.setText(labels[index]);
                tab.setAllCaps(false);
                tab.setTextSize(15);
                tab.setTextColor(LIGHT);
                tab.setMinHeight(dp(52));
                tab.setBackground(box(CARD));
                tab.setContentDescription("Open "+labels[index]+" workspace");
                LinearLayout.LayoutParams cell=new LinearLayout.LayoutParams(0,-2,1);
                cell.setMargins(dp(3),dp(3),dp(3),dp(3));
                bar.addView(tab,cell);
                final Runnable click=actions[index];
                tab.setOnClickListener(v->click.run());
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
            entry.setContentDescription("Open job "+job.title+", "+job.date+" at "+
                appointment.start+". Long-press to drag onto another date in Schedule.");
            entry.setOnLongClickListener(v->{
                ClipData data=ClipData.newPlainText("Accubook Job",job.id);
                return v.startDragAndDrop(data,new View.DragShadowBuilder(v),null,0);
            });
        } catch(Exception e){error(e);}
    }

    private void jobsScreen(){
        currentScreen="jobs";currentJobId=null;currentCustomerId=null;
        try{
            List<WorkspaceStore.Job> jobs=store.jobs();
            jobs.sort((a,b)->a.date.compareTo(b.date));
            screen("Jobs","Search all work · open a job to manage fields, billing and visits");
            navigation();
            button(content,"+ New job",this::chooseCustomer);
            button(content,"Open daybook",this::scheduleScreen);
            EditText search=field(content,"Search jobs","Name, status or address");
            LinearLayout results=new LinearLayout(this);
            results.setOrientation(LinearLayout.VERTICAL);
            content.addView(results);
            Runnable render=()->{
                results.removeAllViews();
                String needle=search.getText().toString().toLowerCase(Locale.ROOT).trim();
                int shown=0;
                for(WorkspaceStore.Job j:jobs){
                    String searchable=(j.title+" "+j.status+" "+j.street+" "+j.date)
                        .toLowerCase(Locale.ROOT);
                    if(!searchable.contains(needle))continue;
                    if(shown++>=120)continue;
                    Button row=button(results,j.date+" · "+j.title+"\n"+j.status+
                        " · $"+j.total,()->job(j.id));
                    row.setContentDescription("Open job "+j.title+" on "+j.date);
                }
                if(shown>120)label(results,"Showing 120 of "+shown+
                    " matches. Type to refine your search.",14,MUTED);
                if(shown==0)label(results,"No matching jobs.",16,MUTED);
            };
            search.addTextChangedListener(new TextWatcher(){
                public void beforeTextChanged(CharSequence value,int st,int ct,int after){}
                public void onTextChanged(CharSequence value,int st,int before,int count){
                    render.run();
                }
                public void afterTextChanged(Editable e){}
            });
            render.run();
        }catch(Exception e){error(e);}
    }


    /**
     * A single explicit offline lookup avoids per-keystroke disk scans and
     * does not create searchable copies of confidential customer information.
     */
    private void universalSearchScreen(){
        currentScreen="lookup";currentJobId=null;currentCustomerId=null;
        screen("Find anything","One search across customers, contacts, jobs, work and documents.");
        navigation();
        EditText query=field(content,"What are you looking for?",
            "Name, phone, address, PO, invoice, VIN, material...");
        query.setSingleLine(true);
        query.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_SEARCH);
        LinearLayout results=new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        Button search=button(content,"Search this device",()->runUniversalLookup(
            query.getText().toString(),results));
        query.setOnEditorActionListener((v,action,event)->{
            if(action==android.view.inputmethod.EditorInfo.IME_ACTION_SEARCH){
                runUniversalLookup(query.getText().toString(),results);
                return true;
            }
            return false;
        });
        content.addView(results,new LinearLayout.LayoutParams(-1,-2));
        label(results,"No account, internet or special keyword required. "+
            "Your search is never sent to a server.",14,MUTED);
    }

    private void runUniversalLookup(String query,LinearLayout results){
        if(SearchTerms.normalize(query).length()<2){
            results.removeAllViews();
            label(results,"Type at least two letters or digits, then tap Search.",15,MUTED);
            return;
        }
        final int request=++lookupRequestSerial;
        results.removeAllViews();
        label(results,"Searching this device…",16,MUTED);
        // No customer data, queries, or matched notes are put into application logs.
        new Thread(()->{
            try{
                List<UniversalLookup.Match> found=new UniversalLookup(this,store,crm)
                    .search(query);
                runOnUiThread(()->{
                    if(!"lookup".equals(currentScreen)||request!=lookupRequestSerial)return;
                    results.removeAllViews();
                    if(found.isEmpty()){
                        label(results,"Nothing found. Try a name, part of an address or "+
                            "a shorter word.",16,MUTED);
                        return;
                    }
                    label(results,found.size()+(found.size()==80?" or more":"")+
                        " results · best matches first",14,MUTED);
                    for(UniversalLookup.Match item:found){
                        button(results,item.title+"\n"+item.detail,()->{
                            switch(item.kind){
                                case "CUSTOMER": customer(item.id); break;
                                case "CONTACT": contactDetails(item.id); break;
                                case "JOB": job(item.id); break;
                                case "CATALOG": catalogScreen(); break;
                                default: notice("Search result","This record cannot be opened.");
                            }
                        });
                    }
                    if(found.size()==80)label(results,"Showing the first 80 matches. "+
                        "Use another word to narrow the results.",14,MUTED);
                });
            }catch(Exception failure){
                runOnUiThread(()->{
                    if(!"lookup".equals(currentScreen)||request!=lookupRequestSerial)return;
                    results.removeAllViews();
                    error(failure);
                    label(results,"Search could not finish. No workspace records were "+
                        "deleted or reset.",15,MUTED);
                });
            }
        },"accubook-local-lookup").start();
    }


    /** Optional repeat-service reminders; never auto-create another job or message a customer. */
    private void serviceDueScreen(){
        currentScreen="service_due";currentJobId=null;currentCustomerId=null;
        try{
            screen("Next services due","A simple local call-back list. You choose who to contact.");
            navigation();
            if(!FeatureSettings.enabled(this,FeatureSettings.RECURRING)){
                label(content,"Turn on Repeat-service due dates in Business → Settings first.",
                    16,MUTED);
                button(content,"Open Settings",this::settingsScreen);
                return;
            }
            List<RecurringServices.Rule> list=new RecurringServices(store).all();
            list.sort((a,b)->{
                String ad=a.dueDate.isEmpty()?"9999-12-31":a.dueDate;
                String bd=b.dueDate.isEmpty()?"9999-12-31":b.dueDate;
                return ad.compareTo(bd);
            });
            int due=0,active=0;
            for(RecurringServices.Rule rule:list){
                if(rule.active)active++;
                if(rule.dueToday())due++;
            }
            label(content,due+" due or overdue by date · "+active+" active reminders",
                19,LIGHT);
            if(due>0)button(content,"Save or print due-service slips (PDF)",
                this::exportServiceDueSlips);
            label(content,"Mileage-only reminders show a target odometer reading. "+
                "They do not assume how far a vehicle has traveled.",14,MUTED);
            if(list.isEmpty())
                label(content,"No repeat service rules yet. Open a job → Overview → "+
                    "Set next service due.",16,MUTED);
            int rendered=0;
            for(RecurringServices.Rule rule:list){
                if(++rendered>120)break;
                WorkspaceStore.Customer person=null;
                for(WorkspaceStore.Customer c:store.customers())
                    if(c.id.equals(rule.customerId)){person=c;break;}
                LinearLayout row=card();
                label(row,rule.label+" · "+
                    (person==null?"Unknown customer":person.displayName()),18,LIGHT);
                label(row,rule.active?(rule.dueToday()?"DUE NOW":
                    "Scheduled"):"Paused",15,rule.dueToday()?0xFFFFCD86:MUTED);
                label(row,(rule.dueDate.isEmpty()?"No calendar due date":
                    "Next due: "+rule.dueDate)+
                    (rule.dueMiles.isEmpty()?"":" · Next odometer: "+rule.dueMiles)+
                    (rule.site.isEmpty()?"":"\nSite/asset: "+rule.site),15,MUTED);
                final RecurringServices.Rule entry=rule;
                button(row,"Open original job",()->job(entry.jobId));
                button(row,"Update after service / edit interval",()->{
                    try{serviceIntervalDialog(jobById(entry.jobId),entry);}
                    catch(Exception e){error(e);}
                });
                button(row,rule.active?"Pause reminder":"Resume reminder",()->{
                    try{
                        new RecurringServices(store).setActive(entry.id,!entry.active);
                        serviceDueScreen();
                    }catch(Exception e){error(e);}
                });
            }
            if(list.size()>120)label(content,
                "Showing the first 120 services. Smaller filtered lists are planned.",14,MUTED);
            label(content,"This module does not automatically notify customers, "+
                "create appointments, read odometers or send data to the cloud.",13,MUTED);
        }catch(Exception failure){error(failure);}
    }


    private void exportServiceDueSlips(){
        Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        save.addCategory(Intent.CATEGORY_OPENABLE);
        save.setType("application/pdf");
        save.putExtra(Intent.EXTRA_TITLE,
            "accubook-due-services-"+java.time.LocalDate.now()+".pdf");
        try{startActivityForResult(save,SERVICE_SLIP_PDF_REQUEST);}
        catch(Exception failure){error(failure);}
    }

    private void serviceIntervalDialog(WorkspaceStore.Job job,RecurringServices.Rule previous){
        LinearLayout fields=form();
        label(fields,"When was this service actually finished? "+
            "Choose how often it is needed. Nothing is sent automatically.",14,MUTED);
        EditText label=field(fields,"Service","Gutter cleaning / oil change");
        label.setText(previous==null?job.title:previous.label);
        EditText site=field(fields,"Site, vehicle or equipment (optional)","Property, VIN or vehicle name");
        site.setText(previous==null?job.street:previous.site);
        EditText last=field(fields,"Last completed on · YYYY-MM-DD",
            java.time.LocalDate.now().toString());
        last.setText(previous==null?java.time.LocalDate.now().toString():previous.lastDate);
        button(fields,"Choose completion date",()->openDate(last));
        EditText month=field(fields,"Every how many months? (0 if mileage only)","6");
        month.setText(previous==null?"6":previous.months);
        month.setInputType(InputType.TYPE_CLASS_NUMBER);
        EditText miles=field(fields,"Last odometer reading (optional)","55812");
        miles.setText(previous==null?"":previous.lastMiles);
        miles.setInputType(InputType.TYPE_CLASS_NUMBER);
        EditText interval=field(fields,"Every how many miles? (0 if date only)","3000");
        interval.setText(previous==null?"0":previous.miles);
        interval.setInputType(InputType.TYPE_CLASS_NUMBER);
        dialog(previous==null?"Set next service":"Update next service",fields,()->{
            try{
                RecurringServices.Rule saved=new RecurringServices(store).save(job,
                    previous==null?null:previous.id,label.getText().toString(),
                    site.getText().toString(),last.getText().toString(),
                    month.getText().toString(),miles.getText().toString(),
                    interval.getText().toString());
                notice("Next service saved",(saved.dueDate.isEmpty()?"Mileage-only reminder":
                    "Due "+saved.dueDate)+
                    (saved.dueMiles.isEmpty()?"":" · "+saved.dueMiles+" miles")+
                    ". Open Home → due services to review.");
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }

    /** Independent contact directory. No automatic customer creation. */
    private void contactsScreen(){
        currentScreen="contacts";currentCustomerId=null;currentJobId=null;
        try{
            List<ContactDirectory.Contact> all=new ContactDirectory(store).all();
            screen("Contacts",all.size()+" people · customers are a separate list");
            navigation();
            button(content,"Import ALL phone contacts",()->requestPhoneContacts(true));
            button(content,"Choose contacts to import",()->requestPhoneContacts(false));
            button(content,"Pick one Android contact",this::pickContact);
            button(content,"+ Add contact manually",()->contactEdit(null));
            label(content,"Importing contacts does not create customers or change jobs. "
                +"Promote only the people you decide to work with.",14,MUTED);
            EditText search=field(content,"Find any contact","Search name, phone or email");
            LinearLayout results=new LinearLayout(this);
            results.setOrientation(LinearLayout.VERTICAL);
            content.addView(results);
            final int[] page={0};
            final int size=55;
            Runnable render=()->{
                results.removeAllViews();
                String needle=search.getText().toString().trim().toLowerCase(Locale.ROOT);
                List<ContactDirectory.Contact> matching=new ArrayList<>();
                for(ContactDirectory.Contact c:all)
                    if((c.name+" "+c.phone+" "+c.email).toLowerCase(Locale.ROOT)
                        .contains(needle))matching.add(c);
                int pages=Math.max(1,(matching.size()+size-1)/size);
                page[0]=Math.max(0,Math.min(page[0],pages-1));
                label(results,matching.size()+" contacts · page "+(page[0]+1)+
                    " of "+pages,14,MUTED);
                int start=page[0]*size;
                for(int i=start;i<Math.min(start+size,matching.size());i++){
                    ContactDirectory.Contact item=matching.get(i);
                    button(results,item.name+"\n"+item.phone+
                        (item.customerId.isEmpty()?" · Contact":" · Customer linked"),
                        ()->contactDetails(item.id));
                }
                LinearLayout bar=new LinearLayout(this);
                bar.setOrientation(LinearLayout.HORIZONTAL);
                results.addView(bar);
                Button previous=button(bar,"← Previous",()->{page[0]--;renderContactsRefresh[0].run();});
                Button next=button(bar,"Next →",()->{page[0]++;renderContactsRefresh[0].run();});
                previous.setEnabled(page[0]>0);
                next.setEnabled(page[0]+1<pages);
            };
            // Pass a stable callback via a one-element holder to avoid recursing
            // inside its own lambda initializer.
            renderContactsRefresh[0]=render;
            search.addTextChangedListener(new TextWatcher(){
                public void beforeTextChanged(CharSequence value,int st,int ct,int after){}
                public void onTextChanged(CharSequence value,int st,int before,int ct){
                    page[0]=0;render.run();
                }
                public void afterTextChanged(Editable value){}
            });
            render.run();
        }catch(Exception e){error(e);}
    }
    private final Runnable[] renderContactsRefresh=new Runnable[1];

    private void contactDetails(String identifier){
        try{
            ContactDirectory.Contact c=null;
            for(ContactDirectory.Contact x:new ContactDirectory(store).all())
                if(x.id.equals(identifier))c=x;
            if(c==null)throw new IOException("Contact no longer available");
            final ContactDirectory.Contact selected=c;
            currentScreen="contact";
            screen(c.name,"Private contact · independent from customers");
            navigation();
            label(content,"Phone: "+(c.phone.isEmpty()?"Not provided":c.phone),17,LIGHT);
            label(content,"Email: "+(c.email.isEmpty()?"Not provided":c.email),16,LIGHT);
            button(content,"Edit contact",()->contactEdit(selected));
            if(c.customerId.isEmpty())
                button(content,"+ Make this contact a customer",
                    ()->promoteContact(selected));
            else{
                final String customerId=c.customerId;
                button(content,"Open linked customer",()->customer(customerId));
            }
            button(content,"Remove contact from Contacts",()->new AlertDialog.Builder(this)
                .setTitle("Delete contact?")
                .setMessage("Only this local directory record is deleted. "
                    +"Any already-created customer remains untouched.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton("Delete",(d,w)->{
                    try{new ContactDirectory(store).delete(selected.id);contactsScreen();}
                    catch(Exception e){error(e);}
                }).show());
        }catch(Exception e){error(e);}
    }
    private void contactEdit(ContactDirectory.Contact existing){
        LinearLayout fields=form();
        EditText name=field(fields,"Contact name","Name");
        EditText phone=field(fields,"Telephone","Phone");
        phone.setInputType(InputType.TYPE_CLASS_PHONE);
        EditText email=field(fields,"Email address","Email");
        email.setInputType(InputType.TYPE_CLASS_TEXT|
            InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        if(existing!=null){
            name.setText(existing.name);phone.setText(existing.phone);
            email.setText(existing.email);
        }
        dialog(existing==null?"New contact":"Edit contact",fields,()->{
            try{
                ContactDirectory directory=new ContactDirectory(store);
                if(existing==null){
                    directory.add(name.getText().toString(),phone.getText().toString(),
                        email.getText().toString());
                    contactsScreen();
                }else{
                    directory.update(existing.id,name.getText().toString(),
                        phone.getText().toString(),email.getText().toString());
                    contactDetails(existing.id);
                }
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }
    private void promoteContact(ContactDirectory.Contact contact){
        new AlertDialog.Builder(this).setTitle("Create customer from this contact?")
            .setMessage("Promote "+contact.name+" to Customers? This is a separate action. "
                +"The original Contacts entry remains available.")
            .setNegativeButton("Not yet",(d,w)->{})
            .setPositiveButton("Create customer",(d,w)->{
                try{
                    for(WorkspaceStore.Customer existing:store.customers()){
                        if((!contact.phone.isEmpty()&&contact.phone.equals(existing.phone))||
                            (!contact.email.isEmpty()&&
                                contact.email.equalsIgnoreCase(existing.email))){
                            new ContactDirectory(store).linkCustomer(contact.id,existing.id);
                            customer(existing.id);
                            notice("Linked existing customer",
                                "Matching customer already exists; no duplicate created.");
                            return;
                        }
                    }
                    WorkspaceStore.Customer created=store.addCustomer("",contact.name,
                        contact.phone,contact.email,"","","","");
                    new ContactDirectory(store).linkCustomer(contact.id,created.id);
                    customer(created.id);
                }catch(Exception e){error(e);}
            }).show();
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
            button(content, "Open contacts directory (separate from customers)",
                this::contactsScreen);
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
            button(content,"Open full month calendar grid",this::calendarScreen);
            // No silent batch publishing on schedule open; explicit calendar action only.
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
            for(LocalDate cursor=first;!cursor.isAfter(last);cursor=cursor.plusDays(1)){
                String day=cursor.toString();
                TextView drop=label(content,
                    (day.equals(LocalDate.now().toString())?"Today · ":"")
                    +cursor.getDayOfWeek()+" · "+day+"\nDrop a job here to reschedule",
                    16,LIGHT);
                if(Build.VERSION.SDK_INT>=28)drop.setAccessibilityHeading(true);
                drop.setBackground(box(CARD));
                drop.setPadding(dp(14),dp(10),dp(12),dp(10));
                drop.setMinHeight(dp(55));
                drop.setContentDescription("Date "+day+". Drop a job here. "
                    +"For accessible rescheduling, open a job and choose Reschedule.");
                final String destination=day;
                drop.setOnDragListener((view,event)->{
                    switch(event.getAction()){
                        case android.view.DragEvent.ACTION_DRAG_STARTED:
                            return event.getClipDescription()!=null &&
                                "Accubook Job".contentEquals(event.getClipDescription().getLabel());
                        case android.view.DragEvent.ACTION_DRAG_ENTERED:
                            view.setBackgroundColor(ACCENT);
                            return true;
                        case android.view.DragEvent.ACTION_DRAG_EXITED:
                            view.setBackground(box(CARD));
                            return true;
                        case android.view.DragEvent.ACTION_DROP:
                            view.setBackground(box(CARD));
                            try{
                                if(event.getClipData()==null ||
                                    event.getClipData().getItemCount()!=1)
                                    throw new IOException("Missing job drag payload");
                                String id=event.getClipData().getItemAt(0).getText().toString();
                                WorkspaceStore.Job moving=jobById(id);
                                store.updateJob(id,destination,moving.status);
                                selectedDate=LocalDate.parse(destination);
                                scheduleScreen();
                                Toast.makeText(this,"Job moved to "+destination,Toast.LENGTH_LONG).show();
                                return true;
                            }catch(Exception error){error(error);return false;}
                        case android.view.DragEvent.ACTION_DRAG_ENDED:
                            view.setBackground(box(CARD));
                            return true;
                        default:return true;
                    }
                });
                int daily=0;
                for(WorkspaceStore.Job j:jobs) {
                    if(!j.date.equals(day))continue;
                    jobRow(j);
                    daily++;matches++;
                }
                if(daily==0)label(content,"No work scheduled.",14,MUTED);
            }
            if(matches==0)
                label(content,"No jobs in this range. Schedule a job to begin.",16,MUTED);
            label(content,"Long-press a job and drag it onto another date, or open a job "
                +"and use the accessible Reschedule calendar/clock. "
                +"Time conflicts and crew capacity are not yet calculated.",13,MUTED);

        } catch (Exception error) { error(error); }
    }

    /** True month grid with accessible date actions, not a disguised job list. */
    private void calendarScreen(){
        currentScreen="calendar";
        currentJobId=null;currentCustomerId=null;
        try{
            LocalDate first=selectedDate.withDayOfMonth(1);
            LocalDate last=first.plusMonths(1).minusDays(1);
            screen("Calendar",first.getMonth()+" "+first.getYear()+
                " · choose a day to view its time-ordered daybook");
            navigation();
            LinearLayout controls=card();
            button(controls,"Previous month",()->{
                selectedDate=selectedDate.minusMonths(1);calendarScreen();
            });
            button(controls,"Go to current month",()->{
                selectedDate=LocalDate.now();calendarScreen();
            });
            button(controls,"Next month",()->{
                selectedDate=selectedDate.plusMonths(1);calendarScreen();
            });
            button(controls,"Jump to any date",()->{
                EditText date=field(controls,"Jump date · YYYY-MM-DD",selectedDate.toString());
                date.setText(selectedDate.toString());
                openDate(date);
                // The date picker writes the field; tapping a day applies selection.
                button(controls,"Show selected calendar date",()->{
                    try{selectedDate=LocalDate.parse(date.getText().toString());calendarScreen();}
                    catch(Exception e){error(e);}
                });
            });
            int offset=first.getDayOfWeek().getValue()-1; // Monday=1
            int cells=((offset+last.getDayOfMonth()+6)/7)*7;
            String[] weekdays={"Mon","Tue","Wed","Thu","Fri","Sat","Sun"};
            LinearLayout names=new LinearLayout(this);
            names.setOrientation(LinearLayout.HORIZONTAL);
            content.addView(names);
            for(String name:weekdays){
                TextView cell=new TextView(this);
                cell.setText(name);
                cell.setGravity(android.view.Gravity.CENTER);
                cell.setTextSize(13);
                cell.setTextColor(MUTED);
                names.addView(cell,new LinearLayout.LayoutParams(0,dp(38),1));
            }
            List<WorkspaceStore.Job> jobs=store.jobs();
            for(int row=0;row<cells/7;row++){
                LinearLayout week=new LinearLayout(this);
                week.setOrientation(LinearLayout.HORIZONTAL);
                content.addView(week,new LinearLayout.LayoutParams(-1,-2));
                for(int day=0;day<7;day++){
                    int dayOfMonth=row*7+day-offset+1;
                    Button tile=new Button(this);
                    tile.setAllCaps(false);
                    tile.setTextSize(14);
                    tile.setMinHeight(dp(68));
                    LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,dp(70),1);
                    params.setMargins(dp(2),dp(2),dp(2),dp(2));
                    week.addView(tile,params);
                    if(dayOfMonth<1||dayOfMonth>last.getDayOfMonth()){
                        tile.setEnabled(false);
                        tile.setText("");
                        tile.setBackgroundTintList(ColorStateList.valueOf(BACKGROUND));
                        continue;
                    }
                    LocalDate date=first.withDayOfMonth(dayOfMonth);
                    int count=0;
                    String color=CrmWorkspace.JOB_COLORS[0];
                    for(WorkspaceStore.Job job:jobs)
                        if(job.date.equals(date.toString())){
                            count++;
                            if(count==1)color=crm.appointment(job).color;
                        }
                    tile.setText(dayOfMonth+(count>0?"\n"+count+" job"+(count>1?"s":""):""));
                    tile.setTextColor(Color.WHITE);
                    if(count>0){
                        int chosen=Color.parseColor(color);
                        tile.setBackgroundTintList(ColorStateList.valueOf(chosen));
                        tile.setTextColor(Color.luminance(chosen)>0.45?Color.BLACK:Color.WHITE);
                    }else tile.setBackgroundTintList(ColorStateList.valueOf(CARD));
                    if(date.equals(LocalDate.now()))tile.setElevation(dp(6));
                    final int jobCount=count;
                    tile.setContentDescription(date+" · "+jobCount+" scheduled jobs. Open day.");
                    tile.setOnClickListener(v->{
                        selectedDate=date;scheduleMode="Day";scheduleScreen();
                    });
                }
            }
            label(content,"Job colors indicate scheduled work; open a day to see the "
                +"customer, start/end time and notes. Route and worker data stay local.",
                14,MUTED);
        }catch(Exception e){error(e);}
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
            CrmWorkspace.ContactPreferences prefs=crm.preferences(c);
            label(content, "Contact: " + c.contact, 17, LIGHT);
            label(content, "Preferred: " + (prefs.call?"Call  ":"")+
                (prefs.sms?"SMS  ":"")+(prefs.email?"Email":"")+
                " · Customer color "+prefs.color,15,LIGHT);
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

    private void backupPasswordDialog(String title,boolean confirm,
                                      java.util.function.Consumer<char[]> result){
        LinearLayout fields=form();
        label(fields,"Use a unique 12+ character passphrase. It is not saved or uploaded. "
            +"Losing it makes the backup unrecoverable.",15,LIGHT);
        EditText password=field(fields,"Passphrase","12 characters or more");
        password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText second=null;
        if(confirm){
            second=field(fields,"Confirm passphrase","Repeat passphrase");
            second.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        }
        final EditText confirmation=second;
        dialog(title,fields,()->{
            char[] pass=password.getText().toString().toCharArray();
            if(pass.length<12||pass.length>512){
                java.util.Arrays.fill(pass,'\0');
                throw new IllegalArgumentException("Passphrase must be 12–512 characters");
            }
            if(confirmation!=null&&!java.util.Arrays.equals(pass,
                confirmation.getText().toString().toCharArray())){
                java.util.Arrays.fill(pass,'\0');
                throw new IllegalArgumentException("Passphrases do not match");
            }
            result.accept(pass);
        });
    }
    /**
     * Default calendar workflow uses Android's event composer, like the working
     * pickup reminder handoff. It needs no calendar-provider write permission.
     * Advanced one-way reconciliation remains available but is never automatic.
     */
    private void calendarSettings(){
        boolean advanced=FeatureSettings.enabled(this,FeatureSettings.ADVANCED_CALENDAR);
        String[] options=advanced?new String[]{
            "Add a job to Calendar app (recommended)",
            "Advanced account sync (experimental)",
            CalendarBridge.enabled(this)?"Disable automatic calendar sync":
                "Calendar sharing privacy explanation"
        }:new String[]{
            "Add a job to Calendar app (recommended)",
            "Calendar sharing privacy explanation"
        };
        new AlertDialog.Builder(this).setTitle("Calendar options")
            .setMessage("For reliable Google Calendar scheduling, choose a job, "
                +"review its event, and save it in your installed Calendar app. "
                +"No background syncing or hidden sharing occurs by default.")
            .setItems(options,(d,index)->{
                if(index==0)chooseJobForCalendar();
                else if(advanced&&index==1)advancedCalendarSettings();
                else if(advanced&&CalendarBridge.enabled(this)){
                    CalendarBridge.setEnabled(this,-1,false);businessScreen();
                }else notice("Calendar privacy","Only explicitly exported events go "
                    +"to your selected Calendar app. Advanced sync must be enabled "
                    +"separately under Settings > Modules.");
            }).setNegativeButton("Close",(d,w)->{}).show();
    }
    private void chooseJobForCalendar(){
        try{
            List<WorkspaceStore.Job> jobs=store.jobs();
            jobs.sort((x,y)->x.date.compareTo(y.date));
            if(jobs.isEmpty()){notice("No jobs scheduled","Create a job first.");return;}
            String[] options=new String[jobs.size()];
            for(int i=0;i<jobs.size();i++)
                options[i]=jobs.get(i).date+" · "+jobs.get(i).title;
            new AlertDialog.Builder(this).setTitle("Choose a job to add to Calendar")
                .setItems(options,(d,index)->addJobToCalendar(jobs.get(index)))
                .setNegativeButton("Cancel",(d,w)->{}).show();
        }catch(Exception e){error(e);}
    }
    private void addJobToCalendar(WorkspaceStore.Job job){
        try{
            CrmWorkspace.Appointment schedule=crm.appointment(job);
            java.time.ZoneId zone=java.time.ZoneId.systemDefault();
            long begin=java.time.LocalDateTime.parse(job.date+"T"+schedule.start)
                .atZone(zone).toInstant().toEpochMilli();
            long finish=java.time.LocalDateTime.parse(job.date+"T"+schedule.end)
                .atZone(zone).toInstant().toEpochMilli();
            if(finish<=begin)throw new IOException("Appointment end precedes start");
            new AlertDialog.Builder(this).setTitle("Review calendar event")
                .setMessage(job.title+"\n"+job.date+" · "+schedule.start+"–"+
                    schedule.end+"\n"+job.street+", "+job.city+"\n\n"
                    +"Choose a calendar account and press Save in the Calendar app. "
                    +"This shares the job title, date/time, site and short daybook note "
                    +"with that calendar provider. Nothing is sent by Accubook. "
                    +"The event is not saved until you confirm in Calendar.")
                .setNegativeButton("Keep private",(d,w)->{})
                .setPositiveButton("Open Calendar editor",(d,w)->{
                    Intent insert=new Intent(Intent.ACTION_INSERT,
                        android.provider.CalendarContract.Events.CONTENT_URI);
                    insert.putExtra(android.provider.CalendarContract.Events.TITLE,
                        job.title);
                    insert.putExtra(android.provider.CalendarContract.EXTRA_EVENT_BEGIN_TIME,
                        begin);
                    insert.putExtra(android.provider.CalendarContract.EXTRA_EVENT_END_TIME,
                        finish);
                    insert.putExtra(android.provider.CalendarContract.Events.EVENT_LOCATION,
                        job.street+", "+job.city+", "+job.state+" "+job.zip);
                    insert.putExtra(android.provider.CalendarContract.Events.DESCRIPTION,
                        "Accubook job · "+job.status+"\n"+schedule.notes);
                    try{startActivity(insert);}
                    catch(Exception failure){
                        error(new IllegalStateException("No compatible Calendar editor "
                            +"is available. Install or enable your calendar app.",
                            failure));
                    }
                }).show();
        }catch(Exception e){error(e);}
    }
    private void advancedCalendarSettings(){
        if(CalendarBridge.enabled(this)){
            new AlertDialog.Builder(this).setTitle("Experimental account sync enabled")
                .setMessage("One-way sync writes job data into the selected account. "
                    +"It can create unexpected calendar events if account settings "
                    +"change. Use manual sync only until device tests pass.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setNeutralButton("Try sync once",(d,w)->syncCalendarNow())
                .setPositiveButton("Disable",(d,w)->{
                    CalendarBridge.setEnabled(this,-1,false);businessScreen();
                }).show();
        }else new AlertDialog.Builder(this)
            .setTitle("Experimental account synchronization")
            .setMessage("This requires Android calendar read/write access and account "
                +"selection. Google calendars can upload job details. "
                +"The recommended event-editor workflow needs no such permissions. "
                +"Turn this on only after understanding data sharing.")
            .setNegativeButton("Not now",(d,w)->{})
            .setPositiveButton("Select calendar",(d,w)->{
                if(checkSelfPermission(Manifest.permission.READ_CALENDAR)!=
                    PackageManager.PERMISSION_GRANTED||
                    checkSelfPermission(Manifest.permission.WRITE_CALENDAR)!=
                    PackageManager.PERMISSION_GRANTED)
                    requestPermissions(new String[]{Manifest.permission.READ_CALENDAR,
                        Manifest.permission.WRITE_CALENDAR},CALENDAR_PERMISSIONS);
                else chooseSyncCalendar();
            }).show();
    }
    private void chooseSyncCalendar(){
        try{
            List<CalendarBridge.CalendarChoice> choices=
                new CalendarBridge(this,store).choices();
            if(choices.isEmpty()){
                notice("No writable calendar","Add a calendar account or use the "
                    +"device calendar application. Local scheduling remains available.");
                return;
            }
            String[] names=new String[choices.size()];
            for(int i=0;i<choices.size();i++)names[i]=choices.get(i).toString();
            new AlertDialog.Builder(this).setTitle("Select destination calendar")
                .setItems(names,(d,index)->{
                    CalendarBridge.CalendarChoice choice=choices.get(index);
                    new AlertDialog.Builder(this).setTitle("Confirm calendar sharing")
                        .setMessage("Copy scheduled jobs and notes to "+choice+
                            "? Calendar events will be visible to anyone with access "
                            +"to that account or shared calendar. This is OFF by default.")
                        .setNegativeButton("Cancel",(dd,w)->{})
                        .setPositiveButton("Enable",(dd,w)->{
                            CalendarBridge.setEnabled(this,choice.id,true);
                            businessScreen();
                            syncCalendarNow();
                        }).show();
                }).setNegativeButton("Cancel",(d,w)->{}).show();
        }catch(Exception e){error(e);}
    }
    private void syncCalendarNow(){
        if(!CalendarBridge.enabled(this))return;
        new Thread(()->{
            try {
                int count=new CalendarBridge(this,store).syncAll();
                runOnUiThread(()->Toast.makeText(this,
                    count+" Accubook jobs reconciled with selected calendar",
                    Toast.LENGTH_LONG).show());
            }catch(Exception e){runOnUiThread(()->error(e));}
        },"accubook-optin-calendar-sync").start();
    }
    private void localPickupReminder(WorkspaceStore.Job job){
        LinearLayout fields=form();
        EditText date=field(fields,"Dumpster pickup date · YYYY-MM-DD","Date");
        date.setText(job.date);
        button(fields,"Choose pickup date",()->openDate(date));
        EditText time=field(fields,"Pickup notification time · HH:mm","09:00");
        time.setText("09:00");
        button(fields,"Choose notification time",()->openClock(time));
        dialog("Local dumpster pickup notification",fields,()->{
            java.time.LocalDateTime when=java.time.LocalDateTime.parse(
                date.getText().toString()+"T"+time.getText().toString());
            long epoch=when.atZone(java.time.ZoneId.systemDefault())
                .toInstant().toEpochMilli();
            if(epoch<System.currentTimeMillis()+30_000)
                throw new IllegalArgumentException("Choose a future pickup time");
            new AlertDialog.Builder(this).setTitle("Confirm local pickup reminder")
                .setMessage("Notify this device around "+date.getText()+" at "+time.getText()+
                    " for dumpster pickup? Android may delay the notification. "
                    +"No data is sent to a remote server.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton("Schedule",(d,w)->{
                    try{
                        if(Build.VERSION.SDK_INT>=33&&
                            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=
                                PackageManager.PERMISSION_GRANTED){
                            pendingPickupJobId=job.id;pendingPickupWhen=epoch;
                            requestPermissions(new String[]{
                                Manifest.permission.POST_NOTIFICATIONS},PICKUP_NOTIFY_PERMISSION);
                            return;
                        }
                        PickupReminders.schedule(this,store,job,epoch);
                        job(job.id);
                        notice("Pickup reminder scheduled",
                            "A local reminder was saved. Timing may be delayed by Android.");
                    }catch(Exception e){error(e);}
                }).show();
        });
    }

    private void createPickupReminder(WorkspaceStore.Job job){
        LinearLayout fields=form();
        EditText date=field(fields,"Pickup date · YYYY-MM-DD","Choose calendar date");
        date.setText(job.date);
        button(fields,"Pick dumpster pickup date",()->openDate(date));
        EditText time=field(fields,"Pickup time · HH:mm","09:00");
        time.setText("09:00");
        button(fields,"Pick pickup time",()->openClock(time));
        dialog("Set a calendar pickup reminder",fields,()->{
            try {
                java.time.LocalDateTime timestamp=java.time.LocalDateTime.parse(
                    date.getText().toString()+"T"+time.getText().toString());
                long start=timestamp.atZone(java.time.ZoneId.systemDefault())
                    .toInstant().toEpochMilli();
                Intent insert=new Intent(Intent.ACTION_INSERT,
                    android.provider.CalendarContract.Events.CONTENT_URI);
                insert.putExtra(android.provider.CalendarContract.Events.TITLE,
                    "Dumpster pickup · "+job.title);
                insert.putExtra(android.provider.CalendarContract.EXTRA_EVENT_BEGIN_TIME,start);
                insert.putExtra(android.provider.CalendarContract.EXTRA_EVENT_END_TIME,
                    start+30*60*1000);
                insert.putExtra(android.provider.CalendarContract.Events.DESCRIPTION,
                    "Accubook contractor pickup reminder. Please configure an event "
                    +"notification in the calendar.");
                insert.putExtra(android.provider.CalendarContract.Events.EVENT_LOCATION,
                    job.street+", "+job.city+", "+job.state+" "+job.zip);
                startActivity(insert); // explicit handoff, calendar app controls save.
            }catch(Exception e){error(e);}
        });
    }

    private void chooseEncryptedBackup(){
        backupPasswordDialog("Encrypt a backup",true,pass->{
            pendingBackupPassword=pass;
            Intent destination=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            destination.addCategory(Intent.CATEGORY_OPENABLE);
            destination.setType("application/octet-stream");
            destination.putExtra(Intent.EXTRA_TITLE,"accubook-backup.acbk");
            try{startActivityForResult(destination,ENCRYPTED_BACKUP_EXPORT);}
            catch(Exception e){
                java.util.Arrays.fill(pass,'\0');
                pendingBackupPassword=null;
                error(e);
            }
        });
    }
    private void chooseEncryptedRestore(){
        new AlertDialog.Builder(this).setTitle("Restore password-encrypted backup?")
            .setMessage("Accubook verifies the password and full AES-GCM authentication "
                +"before replacing the live workspace. The previous workspace stays in "
                +"the rollback snapshot. Verify it before discarding.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Choose file",(d,w)->{
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);
                pick.setType("*/*");
                try{startActivityForResult(pick,ENCRYPTED_BACKUP_IMPORT);}
                catch(Exception e){error(e);}
            }).show();
    }
    private void encryptWorkspace(Uri destination,char[] pass){
        new Thread(()->{
            try(OutputStream out=getContentResolver().openOutputStream(destination,"wt")){
                if(out==null)throw new IOException("Cannot write encrypted backup");
                store.exportBackup(SecureArchive.encryptStream(out,pass));
                runOnUiThread(()->notice("Encrypted backup complete",
                    "File saved. Keep the password private and test a restore."));
            }catch(Exception e){runOnUiThread(()->error(e));}
            finally{java.util.Arrays.fill(pass,'\0');}
        },"accubook-private-export").start();
    }
    private void decryptWorkspace(Uri selected,char[] pass){
        new Thread(()->{
            try(InputStream input=getContentResolver().openInputStream(selected)){
                File plaintext=SecureArchive.decryptToTemp(input,getCacheDir(),pass);
                try(InputStream zip=new FileInputStream(plaintext)){
                    store.restoreBackup(zip);
                }finally{
                    if(plaintext.exists()&&!plaintext.delete())
                        android.util.Log.e("Accubook","Cannot delete sensitive decrypted temp file");
                }
                runOnUiThread(()->{
                    try{
                        store=new WorkspaceStore(this);
                        crm=new CrmWorkspace(store);
                        home();
                        notice("Encrypted restore successful","Inspect records and verify "
                            +"the retained rollback snapshot before proceeding.");
                    }catch(Exception e){error(e);}
                });
            }catch(Exception e){runOnUiThread(()->error(e));}
            finally{java.util.Arrays.fill(pass,'\0');}
        },"accubook-private-restore").start();
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


    /** Contacts are independent from customers until explicitly promoted. */
    private static final class PhoneContact {
        final String id,name,phone;
        PhoneContact(String id,String name,String phone){
            this.id=id;this.name=name;this.phone=phone;
        }
    }
    private void requestBulkContacts(){
        new AlertDialog.Builder(this).setTitle("Import contacts — not customers")
            .setMessage("Import your whole phone address book with one tap, or choose "
                +"individual contacts. Imported people go into Contacts only. "
                +"No customer records or jobs are created.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setNeutralButton("Choose some",(d,w)->requestPhoneContacts(false))
            .setPositiveButton("Import all",(d,w)->new AlertDialog.Builder(this)
                .setTitle("Import all device contacts?")
                .setMessage("Accubook will copy your visible Android contacts into "
                    +"its PRIVATE local Contacts directory. Duplicates are skipped. "
                    +"Nothing is uploaded or converted into customers.")
                .setNegativeButton("Cancel",(dialog,which)->{})
                .setPositiveButton("Import all contacts",
                    (dialog,which)->requestPhoneContacts(true))
                .show()).show();
    }
    private void requestPhoneContacts(boolean all){
        pendingImportAllContacts=all;
        if(checkSelfPermission(Manifest.permission.READ_CONTACTS)!=
            PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{Manifest.permission.READ_CONTACTS},
                BULK_CONTACT_PERMISSION);
        }else if(all)importAllPhoneContacts();
        else showBulkContactPicker();
    }
    /** Single bulk operation; all phone contacts plus contacts without phone numbers. */
    private void importAllPhoneContacts(){
        Toast.makeText(this,"Importing contacts locally…",Toast.LENGTH_LONG).show();
        new Thread(()->{
            try{
                android.content.ContentResolver resolver=getContentResolver();
                Map<String,String> phones=new LinkedHashMap<>(),emails=new LinkedHashMap<>();
                try(Cursor c=resolver.query(
                    ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    new String[]{ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
                        ContactsContract.CommonDataKinds.Phone.NUMBER},null,null,null)){
                    if(c!=null)while(c.moveToNext()){
                        String key=c.getString(0),value=c.getString(1);
                        if(key!=null&&value!=null&&!phones.containsKey(key))
                            phones.put(key,value);
                    }
                }
                try(Cursor c=resolver.query(
                    ContactsContract.CommonDataKinds.Email.CONTENT_URI,
                    new String[]{ContactsContract.CommonDataKinds.Email.CONTACT_ID,
                        ContactsContract.CommonDataKinds.Email.ADDRESS},null,null,null)){
                    if(c!=null)while(c.moveToNext()){
                        String key=c.getString(0),value=c.getString(1);
                        if(key!=null&&value!=null&&!emails.containsKey(key))
                            emails.put(key,value);
                    }
                }
                List<ContactDirectory.ImportEntry> entries=new ArrayList<>();
                try(Cursor c=resolver.query(ContactsContract.Contacts.CONTENT_URI,
                    new String[]{ContactsContract.Contacts._ID,
                        ContactsContract.Contacts.DISPLAY_NAME_PRIMARY},
                    null,null,ContactsContract.Contacts.DISPLAY_NAME_PRIMARY+" ASC")){
                    if(c==null)throw new IOException("Android contacts unavailable");
                    while(c.moveToNext()){
                        String id=c.getString(0),name=c.getString(1);
                        if(id!=null&&name!=null&&!name.trim().isEmpty())
                            entries.add(new ContactDirectory.ImportEntry("android:"+id,
                                name,phones.getOrDefault(id,""),emails.getOrDefault(id,"")));
                    }
                }
                ContactDirectory.Result result=new ContactDirectory(store).importBatch(entries);
                runOnUiThread(()->{
                    contactsScreen();
                    notice("Contact import complete",result.added+
                        " contacts imported, "+result.skipped+" duplicates skipped. "
                        +"Contacts are not customers until you promote them.");
                });
            }catch(Exception ex){runOnUiThread(()->error(ex));}
        },"accubook-all-contact-import").start();
    }

    @Override public void onRequestPermissionsResult(int code,String[] permissions,
                                                     int[] grants) {
        super.onRequestPermissionsResult(code,permissions,grants);
        if(code==PICKUP_NOTIFY_PERMISSION){
            String target=pendingPickupJobId;
            long due=pendingPickupWhen;
            pendingPickupJobId=null;
            pendingPickupWhen=0;
            if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED&&target!=null){
                try{
                    PickupReminders.schedule(this,store,jobById(target),due);
                    notice("Pickup reminder scheduled","An Android local notification is "
                        +"scheduled. Battery optimization may delay delivery.");
                }catch(Exception e){error(e);}
            }else notice("Reminder not scheduled","Notifications were not permitted. "
                +"Enable Accubook notifications and set the pickup time again.");
            return;
        }
        if(code==CALENDAR_PERMISSIONS){
            if(grants.length>=2 &&
                grants[0]==PackageManager.PERMISSION_GRANTED &&
                grants[1]==PackageManager.PERMISSION_GRANTED)
                chooseSyncCalendar();
            else notice("Calendar sync disabled","Calendar read/write permission was not "
                +"granted. The local Accubook schedule is unchanged.");
            return;
        }
        if(code==ROUTE_LOCATION_PERMISSION){
            if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED &&
                routeJobId!=null)startRoute(routeJobId);
            else notice("GPS not enabled","Route recording is optional and stays off.");
            return;
        }
        if(code==BULK_CONTACT_PERMISSION) {
            if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED){
                if(pendingImportAllContacts)importAllPhoneContacts();
                else showBulkContactPicker();
            }else notice("Permission not granted","No address book access. You can "
                +"add a contact manually or use the one-contact Android picker.");
            pendingImportAllContacts=false;
        }
    }

    /** Loads the user's complete permitted contacts, without a fixed result cap. */
    private void showBulkContactPicker() {
        Toast.makeText(this,"Loading contacts…",Toast.LENGTH_SHORT).show();
        new Thread(()->{
            try {
                LinkedHashMap<String,PhoneContact> contacts=new LinkedHashMap<>();
                String[] projection={
                    ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                };
                try(Cursor cursor=getContentResolver().query(
                    ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    projection,null,null,ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME+" ASC")){
                    if(cursor==null)throw new IOException("Cannot browse phone contacts");
                    while(cursor.moveToNext()){
                        String id=cursor.getString(0), name=cursor.getString(1),phone=cursor.getString(2);
                        if(id!=null&&name!=null&&!name.trim().isEmpty()&&!contacts.containsKey(id))
                            contacts.put(id,new PhoneContact(id,name,phone==null?"":phone));
                    }
                }
                runOnUiThread(()->bulkContactDialog(new ArrayList<>(contacts.values())));
            }catch(Exception failure){runOnUiThread(()->error(failure));}
        },"accubook-contact-discovery").start();
    }

    /**
     * Search applies to the entire contact collection. Checked IDs persist across
     * queries/pages; the visible page is just a small, recyclable selection surface.
     */
    private void bulkContactDialog(List<PhoneContact> all) {
        if(all.isEmpty()){notice("No contacts","Your address book has no phone contacts.");return;}
        final Set<String> chosen=new HashSet<>();
        final int[] page={0};
        final int pageSize=60;
        final LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(15),dp(10),dp(15),dp(12));
        final EditText search=new EditText(this);
        search.setSingleLine(true);
        search.setHint("Search any contact by name or phone");
        search.setTextSize(17);
        root.addView(search,new LinearLayout.LayoutParams(-1,dp(52)));
        final TextView status=new TextView(this);
        status.setTextSize(15);
        status.setTextColor(Color.DKGRAY);
        root.addView(status);
        final ScrollView scroll=new ScrollView(this);
        final LinearLayout results=new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(results);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,dp(360)));
        final LinearLayout pager=new LinearLayout(this);
        pager.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(pager);
        final Button previous=new Button(this),next=new Button(this);
        previous.setText("Previous");
        next.setText("Next");
        pager.addView(previous,new LinearLayout.LayoutParams(0,dp(50),1));
        pager.addView(next,new LinearLayout.LayoutParams(0,dp(50),1));
        Runnable render=()->{
            String needle=search.getText().toString().trim().toLowerCase(Locale.ROOT);
            List<PhoneContact> filtered=new ArrayList<>();
            for(PhoneContact c:all)if(c.name.toLowerCase(Locale.ROOT).contains(needle)||
                c.phone.toLowerCase(Locale.ROOT).contains(needle))filtered.add(c);
            int pages=Math.max(1,(filtered.size()+pageSize-1)/pageSize);
            page[0]=Math.max(0,Math.min(page[0],pages-1));
            results.removeAllViews();
            int start=page[0]*pageSize;
            int end=Math.min(filtered.size(),start+pageSize);
            for(int i=start;i<end;i++){
                final PhoneContact contact=filtered.get(i);
                CheckBox box=new CheckBox(this);
                box.setText(contact.name+" · "+contact.phone);
                box.setTextColor(Color.BLACK);
                box.setTextSize(15);
                box.setMinHeight(dp(50));
                box.setChecked(chosen.contains(contact.id));
                box.setOnCheckedChangeListener((widget,checked)->{
                    if(checked)chosen.add(contact.id);else chosen.remove(contact.id);
                    status.setText(filtered.size()+" matching · "+chosen.size()+" selected · Page "
                        +(page[0]+1)+" of "+pages);
                });
                results.addView(box,new LinearLayout.LayoutParams(-1,-2));
            }
            status.setText(filtered.size()+" matching · "+chosen.size()+" selected · Page "
                +(page[0]+1)+" of "+pages);
            previous.setEnabled(page[0]>0);
            next.setEnabled(page[0]+1<pages);
            scroll.scrollTo(0,0);
        };
        search.addTextChangedListener(new TextWatcher(){
            @Override public void beforeTextChanged(CharSequence text,int start,int count,int after){}
            @Override public void onTextChanged(CharSequence text,int start,int before,int count){
                page[0]=0;render.run();
            }
            @Override public void afterTextChanged(Editable text){}
        });
        previous.setOnClickListener(v->{page[0]--;render.run();});
        next.setOnClickListener(v->{page[0]++;render.run();});
        render.run();
        AlertDialog dlg=new AlertDialog.Builder(this)
            .setTitle("Select contacts — "+all.size()+" available")
            .setView(root)
            .setNegativeButton("Cancel",(dialog,index)->{})
            .setNeutralButton("Select visible",null)
            .setPositiveButton("Import selected",null).create();
        dlg.setOnShowListener(d->{
            dlg.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v->{
                String needle=search.getText().toString().trim().toLowerCase(Locale.ROOT);
                List<PhoneContact> filtered=new ArrayList<>();
                for(PhoneContact c:all)if(c.name.toLowerCase(Locale.ROOT).contains(needle)||
                    c.phone.toLowerCase(Locale.ROOT).contains(needle))filtered.add(c);
                for(int i=page[0]*pageSize;i<Math.min(filtered.size(),(page[0]+1)*pageSize);i++)
                    chosen.add(filtered.get(i).id);
                render.run();
            });
            dlg.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
                if(chosen.isEmpty()){Toast.makeText(this,
                    "Select one or more contacts",Toast.LENGTH_SHORT).show();return;}
                boolean[] selected=new boolean[all.size()];
                for(int i=0;i<all.size();i++)selected[i]=chosen.contains(all.get(i).id);
                dlg.dismiss();
                importSelectedContacts(all,selected);
            });
        });
        dlg.show();
    }

    private String emailForContact(String id) {
        try(Cursor c=getContentResolver().query(
            ContactsContract.CommonDataKinds.Email.CONTENT_URI,
            new String[]{ContactsContract.CommonDataKinds.Email.ADDRESS},
            ContactsContract.CommonDataKinds.Email.CONTACT_ID+"=?",
            new String[]{id},null)){
            if(c!=null&&c.moveToFirst())return c.getString(0)==null?"":c.getString(0);
        }catch(Exception ignored){}
        return "";
    }
    private static String phoneKey(String number) {
        if(number==null)return "";
        String digits=number.replaceAll("[^0-9]","");
        return digits.length()>=7?digits:"";
    }
    private void importSelectedContacts(List<PhoneContact> choices,boolean[] selected){
        Toast.makeText(this,"Copying selected contacts…",Toast.LENGTH_SHORT).show();
        new Thread(()->{
            try{
                List<ContactDirectory.ImportEntry> entries=new ArrayList<>();
                for(int i=0;i<choices.size();i++){
                    if(!selected[i])continue;
                    PhoneContact c=choices.get(i);
                    entries.add(new ContactDirectory.ImportEntry("android:"+c.id,
                        c.name,c.phone,emailForContact(c.id)));
                }
                ContactDirectory.Result result=new ContactDirectory(store).importBatch(entries);
                runOnUiThread(()->{
                    contactsScreen();
                    notice("Contact import complete",result.added+
                        " saved as contacts, "+result.skipped+
                        " duplicates skipped. No customers created.");
                });
            }catch(Exception failure){runOnUiThread(()->error(failure));}
        },"accubook-selected-contact-import").start();
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
                    if("Completed".equals(statuses[index])){
                        List<String> incomplete=new JobTemplates(store).missingRequired(job);
                        if(!incomplete.isEmpty()){
                            notice("Complete required fields first",
                                "Open the job checklist and finish: "+
                                    String.join(", ",incomplete));
                            return;
                        }
                    }
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

    private void photoActionMenu(WorkspaceStore.Job job,String name,int index,int count,View source){
        List<String> actions=new ArrayList<>();
        if(index>0)actions.add("Move up");
        if(index<count-1)actions.add("Move down");
        if(count>1)actions.add("Drag to reorder");
        actions.add("Delete photo");
        new AlertDialog.Builder(this).setTitle("Photo "+(index+1))
            .setItems(actions.toArray(new String[0]),(d,which)->{
                String choice=actions.get(which);
                if(choice.equals("Drag to reorder")){
                    ClipData dragData=ClipData.newPlainText("AccubookPhoto",name);
                    source.startDragAndDrop(dragData,new View.DragShadowBuilder(source),null,0);
                }else if(choice.equals("Delete photo")){
                    new AlertDialog.Builder(this).setTitle("Delete this photo?")
                        .setMessage("This cannot be undone. Export a backup first.")
                        .setNegativeButton("Keep",(dialog,w)->{})
                        .setPositiveButton("Delete",(dialog,w)->{
                            try{store.deletePhoto(job,name);job(job.id);}
                            catch(Exception error){error(error);}
                        }).show();
                }else{
                    try{
                        store.movePhoto(job,name,index+(choice.equals("Move up")?-1:1));
                        job(job.id);
                    }catch(Exception error){error(error);}
                }
            }).setNegativeButton("Cancel",(d,w)->{}).show();
    }
    private Bitmap photoBitmap(File file,int maxDimension)throws IOException{
        if(Build.VERSION.SDK_INT>=28){
            android.graphics.ImageDecoder.Source source=
                android.graphics.ImageDecoder.createSource(file);
            return android.graphics.ImageDecoder.decodeBitmap(source,(decoder,info,sourceInfo)->{
                android.util.Size dimensions=info.getSize();
                int w=dimensions.getWidth(),h=dimensions.getHeight();
                if(w<=0||h<=0)throw new IllegalArgumentException("Invalid photo dimensions");
                double divisor=Math.max(1.0,Math.max(w,h)/(double)maxDimension);
                decoder.setTargetSize(Math.max(1,(int)(w/divisor)),
                    Math.max(1,(int)(h/divisor)));
                decoder.setAllocator(android.graphics.ImageDecoder.ALLOCATOR_SOFTWARE);
            });
        }
        BitmapFactory.Options opts=new BitmapFactory.Options();
        opts.inJustDecodeBounds=true;
        BitmapFactory.decodeFile(file.getAbsolutePath(),opts);
        if(opts.outWidth<=0||opts.outHeight<=0)throw new IOException("Unsupported photo codec");
        opts.inJustDecodeBounds=false;
        opts.inSampleSize=1;
        while(opts.outWidth/opts.inSampleSize>maxDimension||
              opts.outHeight/opts.inSampleSize>maxDimension)opts.inSampleSize*=2;
        Bitmap image=BitmapFactory.decodeFile(file.getAbsolutePath(),opts);
        if(image==null)throw new IOException("Photo decoder returned no image");
        return image;
    }

    private void showPhotoPreview(WorkspaceStore.Job job,String name){
        try{
            Bitmap image=photoBitmap(store.photoFile(job,name),1600);
            ImageView preview=new ImageView(this);
            preview.setImageBitmap(image);
            preview.setAdjustViewBounds(true);
            preview.setContentDescription("Large preview of job photo");
            new AlertDialog.Builder(this).setTitle("Job photo")
                .setView(preview).setPositiveButton("Close",(d,w)->{}).show();
        }catch(Exception e){error(e);}
    }

    private void photoTile(LinearLayout row,WorkspaceStore.Job job,String name,
            int number,int count){
        LinearLayout panel=new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(9),dp(8),dp(9),dp(12));
        panel.setBackground(box(CARD));
        LinearLayout.LayoutParams margins=new LinearLayout.LayoutParams(0,-2,1);
        margins.setMargins(dp(3),dp(5),dp(3),dp(5));
        row.addView(panel,margins);
        LinearLayout heading=new LinearLayout(this);
        heading.setOrientation(LinearLayout.HORIZONTAL);
        panel.addView(heading);
        TextView label=label(heading,"Photo "+number,15,LIGHT);
        label.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
        Runnable actions=()->photoActionMenu(job,name,number-1,count,panel);
        fieldMoreButton(heading,"photo "+number,actions);
        panel.setOnLongClickListener(v->{actions.run();return true;});
        label.setOnLongClickListener(v->{actions.run();return true;});
        panel.setOnDragListener((target,event)->{
            switch(event.getAction()){
                case android.view.DragEvent.ACTION_DRAG_STARTED:
                    return event.getClipDescription()!=null &&
                        "AccubookPhoto".equals(String.valueOf(event.getClipDescription().getLabel()));
                case android.view.DragEvent.ACTION_DRAG_ENTERED:
                    panel.setAlpha(0.65f);return true;
                case android.view.DragEvent.ACTION_DRAG_EXITED:
                case android.view.DragEvent.ACTION_DRAG_ENDED:
                    panel.setAlpha(1f);return true;
                case android.view.DragEvent.ACTION_DROP:
                    panel.setAlpha(1f);
                    try{
                        String dragged=event.getClipData().getItemAt(0).coerceToText(this).toString();
                        store.movePhoto(job,dragged,number-1);
                        job(job.id);
                    }catch(Exception e){error(e);}
                    return true;
                default:return true;
            }
        });
        try{
            Bitmap thumb=photoBitmap(store.photoFile(job,name),420);
            ImageView thumbnail=new ImageView(this);
            thumbnail.setImageBitmap(thumb);
            thumbnail.setScaleType(ImageView.ScaleType.CENTER_CROP);
            thumbnail.setContentDescription("Open photo "+number+" of "+count);
            panel.addView(thumbnail,new LinearLayout.LayoutParams(-1,dp(150)));
            thumbnail.setOnClickListener(v->showPhotoPreview(job,name));
            thumbnail.setOnLongClickListener(v->{actions.run();return true;});
        }catch(Exception exception){
            label(panel,"Preview unavailable. Use ⋮ to reorder or delete.",13,MUTED);
        }
    }


    /** User-controlled visual modules; TalkBack itself is controlled by Android. */
    private void settingsScreen(){
        currentScreen="settings";
        currentCustomerId=null;
        currentJobId=null;
        screen("Settings","Keep only the tools you use. Hidden features never erase records.");
        navigation();
        button(content,"Quick setup · choose how you work",
            ()->openBusinessSetup());
        section("Modules");
        label(content,"Feature switches change visible tools only, not customer data. "
            +"Turn any module back on to restore its screens and stored records.",15,MUTED);
        for(int i=0;i<FeatureSettings.KEYS.length;i++){
            final String key=FeatureSettings.KEYS[i];
            android.widget.Switch toggle=new android.widget.Switch(this);
            toggle.setText(FeatureSettings.LABELS[i]);
            toggle.setTextColor(LIGHT);
            toggle.setTextSize(16);
            toggle.setMinHeight(dp(56));
            toggle.setChecked(FeatureSettings.enabled(this,key));
            content.addView(toggle,new LinearLayout.LayoutParams(-1,-2));
            toggle.setOnCheckedChangeListener((button,enabled)->{
                try{
                    FeatureSettings.set(this,key,enabled);
                    if(key.equals(FeatureSettings.ADVANCED_CALENDAR)&&!enabled)
                        CalendarBridge.setEnabled(this,-1,false);
                    Toast.makeText(this,(enabled?"Enabled: ":"Hidden: ")+
                        toggle.getText(),Toast.LENGTH_SHORT).show();
                }catch(Exception error){
                    settingsScreen(); // Re-read the persisted value; avoid recursive switch callbacks.
                    error(error);
                }
            });
        }
        button(content,"? Help · simple steps and searchable answers",this::helpScreen);
        section("Accessibility");
        label(content,"Accubook uses labeled actions and optional gesture shortcuts. "
            +"The three-dot field menu supports touch and screen readers without "
            +"cluttering normal screens. TalkBack is an Android system service; "
            +"this app cannot turn it on by itself.",15,MUTED);
        button(content,"Open Android TalkBack / accessibility settings",()->{
            try{startActivity(new Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS));}
            catch(Exception error){error(error);}
        });
        section("Planned modules");
        label(content,"Automatic repeat-job creation, customer outreach, multi-property "
            +"history, route-density optimization and full accounts payable/general "
            +"ledger controls remain unimplemented. Due-date lists are local and manual.",14,MUTED);
    }


    /** Searchable, permission-free help. Show the basics first, not a wall of text. */
    private void helpScreen(){
        currentScreen="help";
        currentJobId=null;currentCustomerId=null;
        screen("Help · get it done","Point, tap and work. Search only if you need an answer.");
        navigation();
        section("Three things to do first");
        label(content,"1. Add a customer.  2. Create a job.  3. Work → Invoice.",17,LIGHT);
        button(content,"＋ Add a customer",this::customerDialog);
        button(content,"＋ Create a job",this::chooseCustomer);
        EditText query=field(content,"Find help","photos, cash, invoice, reorder...");
        LinearLayout results=new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        content.addView(results);
        final boolean[] expanded={false};
        Runnable refresh=()->{
            results.removeAllViews();
            List<HelpTopics.Topic> found=HelpTopics.search(query.getText().toString());
            int limit=query.length()==0 && !expanded[0]?5:found.size();
            int count=0;
            for(HelpTopics.Topic article:found){
                if(count++>=limit)break;
                Button item=button(results,article.title+"  ›",()->
                    new AlertDialog.Builder(this).setTitle(article.title)
                        .setMessage(article.full())
                        .setPositiveButton("Got it",(whichDialog,which)->{})
                        .show());
                item.setBackgroundTintList(ColorStateList.valueOf(CARD));
            }
            if(found.isEmpty())label(results,"No help found. Try a shorter word.",15,MUTED);
            if(found.size()>limit){
                button(results,"Show all "+found.size()+" help topics",()->{
                    expanded[0]=true;
                    results.removeAllViews();
                    for(HelpTopics.Topic article:found)
                        button(results,article.title+"  ›",()->
                            notice(article.title,article.full()));
                });
            }
        };
        query.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){
                refresh.run();
            }
            public void afterTextChanged(Editable value){}
        });
        refresh.run();
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
            button(content,"Apply Jules Gutter Cleaning profile",()->
                new AlertDialog.Builder(this)
                .setTitle("Apply business profile?")
                .setMessage("Replace the current business name/address/phone/email with Jules "
                    +"Gutter Cleaning? Your logo, document terms and other settings remain.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton("Apply",(d,w)->{
                    try{
                        CrmWorkspace.Branding old=crm.branding();
                        crm.saveBranding("Jules Gutter Cleaning",
                            "15 Ward Street, Hingham, MA 02043","267-667-2321",
                            "julesguttercleaning@gmail.com",old.accent,old.terms,old.footer);
                        businessScreen();
                    }catch(Exception e){error(e);}
                }).show());
            button(content,"Choose business logo",this::pickLogo);
            button(content,"Settings · features and accessibility",this::settingsScreen);
            button(content,"Quick setup · tailor Accubook to your business",
                ()->openBusinessSetup());
            if(FeatureSettings.enabled(this,FeatureSettings.CATALOG))
                button(content,"Manage item and service pricebook",this::catalogScreen);
            button(content,"Customize master job fields / checklists",
                this::masterJobTemplateScreen);
            section("Expenses and costs");
            button(content,"Record a manual expense",this::expenseDialog);
            BigDecimal expenseSum=BigDecimal.ZERO;
            for(CrmWorkspace.Expense expense:crm.expenses())
                expenseSum=expenseSum.add(new BigDecimal(expense.amount));
            label(content,"Recorded expenses: $"+expenseSum.toPlainString(),18,LIGHT);
            for(CrmWorkspace.Expense expense:crm.expenses()){
                LinearLayout row=card();
                label(row,expense.date+" · "+expense.category+" · $"+expense.amount,16,LIGHT);
                label(row,expense.description,14,MUTED);
                button(row,"Delete expense (confirm)",()->new AlertDialog.Builder(this)
                    .setTitle("Delete expense?")
                    .setMessage("This removes $"+expense.amount+" from category "
                        +expense.category+". Export accounting records first.")
                    .setNegativeButton("Keep",(d,w)->{})
                    .setPositiveButton("Delete",(d,w)->{
                        try{crm.deleteExpense(expense.id);businessScreen();}
                        catch(Exception e){error(e);}
                    }).show());
            }
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
            label(content,"Recorded job value: $"+draftTotal.toPlainString(),17,LIGHT);
            label(content,"Payments recorded: $"+received.toPlainString(),17,LIGHT);
            label(content,"Job value minus receipts (not a bank balance): $"+
                draftTotal.subtract(received).toPlainString(),16,LIGHT);
            label(content,"Estimates manually marked sent: "+sent,15,LIGHT);
            for(Map.Entry<String,BigDecimal> item:totals.entrySet())
                label(content,item.getKey()+" ledger: $"+item.getValue().toPlainString(),17,LIGHT);
            label(content,"No bank, PayPal or Cash App account connection is made. "
                +"These are manual offline ledger entries, not verified settlements.",14,MUTED);
            button(content,"Create fictional test business data",this::createTestBusiness);
            section("Optional calendar integration");
            label(content,"Device/Google calendar sync: "+(
                CalendarBridge.enabled(this)?"Opted in":"Off (private default)"),15,LIGHT);
            button(content,"Calendar · share a job / advanced settings",
                this::calendarSettings);
            section("Privacy and protection");
            boolean protectedApp=UnlockActivity.isEnabled(this);
            label(content,"App unlock: "+(protectedApp?"Fingerprint/device PIN enabled":
                "Not enabled"),16,LIGHT);
            button(content,protectedApp?"Disable app unlock":"Enable fingerprint / device PIN",
                this::configureAppLock);
            label(content,"Android authentication protects the app UI. The portable "
                +"workspace and ordinary ZIP backups remain unencrypted. "
                +"An app lock alone is not encryption at rest.",13,MUTED);
            section("Reporting and accounting export");
            button(content,"Quick PDF financial report",()->chooseReportExport(true));
            button(content,"Custom accounting CSV ZIP",()->chooseReportExport(false));
            label(content,"Choose exactly which sections, payment methods and expense "
                +"categories leave Accubook. A PDF is a quick summary; a ZIP contains "
                +"selected editable CSV records. No direct QuickBooks connection exists.",
                14,MUTED);
            section("Workspace safety");
            button(content,"Create encrypted backup (.acbk)",this::chooseEncryptedBackup);
            button(content,"Restore encrypted backup (.acbk)",this::chooseEncryptedRestore);
            button(content,"Restore workspace from ZIP",this::selectRestore);
            if(store.hasRollbackSnapshot()){
                button(content,"Revert last restored workspace",this::revertSnapshot);
                button(content,"Discard verified rollback snapshot",this::discardPreviousSnapshot);
            }
            button(content,"Export full workspace backup",()->{
                pendingBackup=true;
                pendingInvoice=null;
                document("accubook-workspace.zip","application/zip");
            });
        }catch(Exception e){error(e);}
    }

    private void configureAppLock() {
        if(UnlockActivity.isEnabled(this)){
            new AlertDialog.Builder(this).setTitle("Disable app unlock?")
                .setMessage("Accubook will no longer require Android fingerprint or device "
                    +"PIN when it opens. This does not encrypt or decrypt existing files.")
                .setNegativeButton("Keep lock",(d,w)->{})
                .setPositiveButton("Disable",(d,w)->{
                    UnlockActivity.setEnabled(this,false);
                    getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
                    businessScreen();
                }).show();
            return;
        }
        if(!UnlockActivity.isSecure(this)){
            notice("Android screen lock required",
                "Configure a secure Android PIN, password or pattern in device settings "
                +"first, then return here.");
            return;
        }
        new AlertDialog.Builder(this).setTitle("Enable fingerprint / device PIN?")
            .setMessage("Accubook will request your enrolled biometric or device screen "
                +"lock credential when opening. It also hides screenshots while locked. "
                +"This protects app access, but does NOT encrypt the on-disk workspace.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Enable",(d,w)->{
                UnlockActivity.setEnabled(this,true);
                getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
                businessScreen();
            }).show();
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
            button(fields,"Open custom brand color picker",()->
                chooseAnyColor(color.getText().toString(),color::setText));
            EditText terms=multiline(fields,"Default payment terms",brand.terms);
            EditText footer=multiline(fields,"Footer / business information",brand.footer);
            dialog("Default estimate and invoice template",fields,()->{
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
        intent.putExtra("estimate",quote);
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
        chooseAnyColor(chosen[0],value->{
            chosen[0]=value;
            button.setText("Custom color: "+value);
            int color=Color.parseColor(value);
            button.setBackgroundTintList(ColorStateList.valueOf(color));
            button.setTextColor(Color.luminance(color)>0.45?Color.BLACK:Color.WHITE);
        });
    }

    /** Actual draggable rainbow/gradient GUI, no RGB channel sliders. */
    private void chooseAnyColor(String initial,java.util.function.Consumer<String> accept){
        int chosen;
        try{chosen=Color.parseColor(initial);}catch(Exception ignored){chosen=ACCENT;}
        LinearLayout wrapper=new LinearLayout(this);
        wrapper.setOrientation(LinearLayout.VERTICAL);
        wrapper.setPadding(dp(15),dp(8),dp(15),dp(14));
        TextView instructions=new TextView(this);
        instructions.setText("Drag across the rainbow to choose a color. "
            +"Touch the large colored square to adjust the shade.");
        instructions.setTextColor(Color.DKGRAY);
        instructions.setTextSize(16);
        wrapper.addView(instructions);
        ColorSpectrumPicker spectrum=new ColorSpectrumPicker(this,chosen);
        wrapper.addView(spectrum,new LinearLayout.LayoutParams(-1,dp(300)));
        TextView sample=new TextView(this);
        sample.setText("Preview · "+spectrum.hex());
        sample.setGravity(android.view.Gravity.CENTER);
        sample.setTextSize(17);
        sample.setMinHeight(dp(55));
        wrapper.addView(sample);
        Runnable refresh=()->{
            int color=spectrum.chosenColor();
            sample.setBackground(box(color));
            sample.setTextColor(Color.luminance(color)>0.45?Color.BLACK:Color.WHITE);
            sample.setText("Preview · "+spectrum.hex());
        };
        spectrum.onChanged(refresh);refresh.run();
        // Optional exact entry for expert users; no need for sliders or codes.
        EditText expert=new EditText(this);
        expert.setSingleLine(true);
        expert.setTextColor(Color.DKGRAY);
        expert.setHint("Optional exact #HEX code");
        expert.setContentDescription("Optional exact six digit hex color");
        expert.setInputType(InputType.TYPE_CLASS_TEXT|
            InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        wrapper.addView(expert,new LinearLayout.LayoutParams(-1,dp(50)));
        LinearLayout swatches=new LinearLayout(this);
        swatches.setOrientation(LinearLayout.HORIZONTAL);
        wrapper.addView(swatches);
        String[] names={"Blue","Green","Orange","Purple","Red"};
        int[] swatchColors={0xff287bd0,0xff178a64,0xffe78b38,0xff8955ca,0xffc84857};
        for(int i=0;i<names.length;i++){
            final int tint=swatchColors[i];
            Button swatch=new Button(this);
            swatch.setText("");
            swatch.setContentDescription("Select "+names[i]+" color");
            swatch.setMinHeight(dp(44));
            swatch.setBackgroundTintList(ColorStateList.valueOf(tint));
            LinearLayout.LayoutParams size=new LinearLayout.LayoutParams(0,dp(44),1);
            size.setMargins(dp(3),dp(2),dp(3),dp(2));
            swatches.addView(swatch,size);
            swatch.setOnClickListener(v->spectrum.setChosenColor(tint));
        }
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Pick a color")
            .setView(wrapper)
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Use this color",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            .setOnClickListener(v->{
                String typed=expert.getText().toString().trim().toUpperCase(Locale.ROOT);
                String hex=typed.isEmpty()?spectrum.hex():typed;
                if(!hex.matches("#[A-F0-9]{6}")){
                    expert.setError("Use six-digit #HEX or choose visually");
                    return;
                }
                accept.accept(hex);
                dialog.dismiss();
            }));
        dialog.show();
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
                        store.addPhoto(selected,stream,
                            getContentResolver().getType(uri));
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
        pendingAttachmentExportId=attachment.id;
        pendingAttachmentExportJob=job.id;
        Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        save.addCategory(Intent.CATEGORY_OPENABLE);
        save.setType(attachment.mime.isEmpty()?"application/octet-stream":attachment.mime);
        save.putExtra(Intent.EXTRA_TITLE,attachment.name);
        try{startActivityForResult(save,ATTACHMENT_EXPORT_REQUEST);}
        catch(Exception e){error(e);}
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

    private void clockInDialog(WorkspaceStore.Job job) {
        LinearLayout fields=form();
        EditText worker=field(fields,"Worker name (required)","Worker or team member");
        EditText notes=multiline(fields,"Work session notes","");
        dialog("Clock in for this job",fields,()->{
            try{
                crm.clockIn(job,worker.getText().toString(),notes.getText().toString());
                job(job.id);
                Toast.makeText(this,"Clock in saved",Toast.LENGTH_SHORT).show();
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }
    private void clockOutConfirm(WorkspaceStore.Job job,CrmWorkspace.TimeEntry record){
        new AlertDialog.Builder(this).setTitle("Clock out "+record.worker+"?")
            .setMessage("Confirm departure and record elapsed time at this job. "
                +"The original time entry will be retained.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Clock out",(d,w)->{
                try{
                    crm.clockOut(job,record.id);
                    job(job.id);
                }catch(Exception e){error(e);}
            }).show();
    }

    private void chooseReportExport(boolean pdf){
        try{
            LinearLayout fields=form();
            label(fields,pdf?
                "Quick PDF totals only. Choose what to summarize. No customer names, "
                    +"payment references, or itemized expenses appear in a quick PDF.":
                "Export ONLY checked sections and selected payment methods and expense "
                    +"categories into local CSV files. QuickBooks mapping is manual.",
                16,LIGHT);
            CheckBox[] sections=new CheckBox[BusinessReports.SECTIONS.length];
            for(int i=0;i<sections.length;i++)
                sections[i]=checkbox(fields,BusinessReports.SECTIONS[i],i==1);

            LinearLayout methodGroup=new LinearLayout(this);
            methodGroup.setOrientation(LinearLayout.VERTICAL);
            fields.addView(methodGroup);
            label(methodGroup,"Payment methods to include (none chosen by default)",16,LIGHT);
            CheckBox[] methods=new CheckBox[ReportSelection.PAYMENT_METHODS.length];
            for(int i=0;i<methods.length;i++)
                methods[i]=checkbox(methodGroup,ReportSelection.PAYMENT_METHODS[i],false);
            button(methodGroup,"Select every payment method",()->{
                for(CheckBox check:methods)check.setChecked(true);
            });
            button(methodGroup,"Clear payment selection",()->{
                for(CheckBox check:methods)check.setChecked(false);
            });
            methodGroup.setVisibility(View.GONE);
            sections[3].setOnCheckedChangeListener((view,checked)->
                methodGroup.setVisibility(checked?View.VISIBLE:View.GONE));

            LinearLayout expenseGroup=new LinearLayout(this);
            expenseGroup.setOrientation(LinearLayout.VERTICAL);
            fields.addView(expenseGroup);
            label(expenseGroup,"Expense categories to include (none chosen by default)",
                16,LIGHT);
            java.util.TreeSet<String> labels=new java.util.TreeSet<>();
            for(CrmWorkspace.Expense expense:crm.expenses())
                if(!expense.category.trim().isEmpty())labels.add(expense.category);
            String[] categories=labels.toArray(new String[0]);
            CheckBox[] categoryChecks=new CheckBox[categories.length];
            for(int i=0;i<categories.length;i++)
                categoryChecks[i]=checkbox(expenseGroup,categories[i],false);
            if(categories.length==0)
                label(expenseGroup,"No expense categories recorded. "
                    +"Record an expense before exporting this section.",14,MUTED);
            else{
                button(expenseGroup,"Select every expense category",()->{
                    for(CheckBox check:categoryChecks)check.setChecked(true);
                });
                button(expenseGroup,"Clear expense selection",()->{
                    for(CheckBox check:categoryChecks)check.setChecked(false);
                });
            }
            expenseGroup.setVisibility(View.GONE);
            sections[4].setOnCheckedChangeListener((view,checked)->
                expenseGroup.setVisibility(checked?View.VISIBLE:View.GONE));
            label(fields,"Nothing is uploaded. Generated documents are saved to the "
                +"location you explicitly choose. Never use a CSV ZIP as a workspace backup.",
                14,MUTED);
            dialog(pdf?"Configure quick PDF report":"Configure accounting CSV ZIP",fields,()->{
                boolean[] chosen=new boolean[sections.length];
                for(int i=0;i<sections.length;i++)chosen[i]=sections[i].isChecked();
                java.util.Set<String> chosenMethods=new java.util.LinkedHashSet<>();
                for(int i=0;i<methods.length;i++)
                    if(chosen[3]&&methods[i].isChecked())chosenMethods.add(ReportSelection.PAYMENT_METHODS[i]);
                java.util.Set<String> chosenCategories=new java.util.LinkedHashSet<>();
                for(int i=0;i<categories.length;i++)
                    if(chosen[4]&&categoryChecks[i].isChecked())chosenCategories.add(categories[i]);
                ReportSelection selection=new ReportSelection(
                    chosen,chosenMethods,chosenCategories);
                pendingReportSections=selection.sections();
                pendingReportMethods=selection.methods().toArray(new String[0]);
                pendingReportCategories=selection.categories().toArray(new String[0]);
                pendingReportPdf=pdf;
                Intent destination=new Intent(Intent.ACTION_CREATE_DOCUMENT);
                destination.addCategory(Intent.CATEGORY_OPENABLE);
                destination.setType(pdf?"application/pdf":"application/zip");
                destination.putExtra(Intent.EXTRA_TITLE,
                    pdf?"accubook-financial-summary.pdf":"accubook-selected-accounting.zip");
                try{startActivityForResult(destination,REPORT_EXPORT_REQUEST);}
                catch(Exception failure){
                    pendingReportSections=null;
                    pendingReportMethods=null;
                    pendingReportCategories=null;
                    error(failure);
                }
            });
        }catch(Exception error){error(error);}
    }

    private void expenseDialog(){
        LinearLayout fields=form();
        EditText date=field(fields,"Expense date · YYYY-MM-DD","YYYY-MM-DD");
        date.setText(LocalDate.now().toString());
        button(fields,"Choose expense date",()->openDate(date));
        EditText category=field(fields,"Category (required)","Fuel, tools, materials...");
        EditText description=field(fields,"Description (required)","Supplies for project");
        EditText amount=field(fields,"Expense amount (USD)","0.00");
        amount.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);
        dialog("New manual expense",fields,()->{
            // Validate before dismissing the form.
            LocalDate.parse(date.getText().toString().trim());
            CrmWorkspace.money(amount.getText().toString(),true);
            String when=date.getText().toString(),cat=category.getText().toString(),
                desc=description.getText().toString(),sum=amount.getText().toString();
            if(cat.trim().isEmpty()||desc.trim().isEmpty())
                throw new IllegalArgumentException("Expense category and description required");
            new AlertDialog.Builder(this).setTitle("Confirm expense")
                .setMessage("Record $"+sum+" in category "+cat+"? "
                    +"This is a manual accounting entry, not a bank transaction.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton("Record",(d,w)->{
                    try{crm.addExpense(when,cat,desc,sum);businessScreen();}
                    catch(Exception e){error(e);}
                }).show();
        });
    }

    private void toggleRoute(WorkspaceStore.Job job){
        if(routeListener!=null){
            stopRoute();
            job(job.id);
            return;
        }
        new AlertDialog.Builder(this).setTitle("Record route locally?")
            .setMessage("Accubook will collect GPS coordinates only while this screen "
                +"is in the foreground. Coordinates are stored in your local workspace "
                +"and included in ordinary ZIP exports; no location is uploaded. "
                +"Opening a map externally later will require another confirmation.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Enable GPS",(d,w)->{
                if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=
                    PackageManager.PERMISSION_GRANTED){
                    routeJobId=job.id;
                    requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION},
                        ROUTE_LOCATION_PERMISSION);
                }else startRoute(job.id);
            }).show();
    }
    private void startRoute(String jobId){
        try{
            if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=
                PackageManager.PERMISSION_GRANTED)
                throw new SecurityException("Precise location permission is required");
            stopRoute();
            routeJobId=jobId;
            locationManager=(android.location.LocationManager)
                getSystemService(android.content.Context.LOCATION_SERVICE);
            if(locationManager==null||
                !locationManager.isProviderEnabled(android.location.LocationManager.GPS_PROVIDER))
                throw new IOException("Enable GPS in Android location settings");
            routeListener=new android.location.LocationListener(){
                @Override public void onLocationChanged(android.location.Location location){
                    try{
                        if(routeJobId!=null&&location!=null&&location.hasAccuracy()&&
                            location.getAccuracy()<=150){
                            crm.recordLocation(jobById(routeJobId),
                                location.getLatitude(),location.getLongitude(),
                                location.getAccuracy());
                        }
                    }catch(Exception failure){
                        android.util.Log.e("Accubook","Cannot save route point",failure);
                        runOnUiThread(()->{stopRoute();error(failure);});
                    }
                }
                @Override public void onStatusChanged(String provider,int status,Bundle extras){}
                @Override public void onProviderEnabled(String provider){}
                @Override public void onProviderDisabled(String provider){
                    runOnUiThread(()->{
                        stopRoute();
                        notice("Route paused","GPS was disabled. No background tracking continues.");
                    });
                }
            };
            locationManager.requestLocationUpdates(
                android.location.LocationManager.GPS_PROVIDER,15000,20f,routeListener);
            notice("Local route started","Accubook will record GPS while app is visible. "
                +"Leaving the app stops recording.");
        }catch(Exception e){stopRoute();error(e);}
    }
    private void stopRoute(){
        if(locationManager!=null&&routeListener!=null)
            try{locationManager.removeUpdates(routeListener);}catch(Exception ignored){}
        routeListener=null;routeJobId=null;
    }
    private void openRouteInOSM(WorkspaceStore.Job job) {
        try{
            List<CrmWorkspace.RoutePoint> route=crm.routePoints(job);
            if(route.isEmpty()){notice("No route points","Start local route tracking first.");return;}
            CrmWorkspace.RoutePoint point=route.get(route.size()-1);
            new AlertDialog.Builder(this).setTitle("Share a location with OpenStreetMap?")
                .setMessage("Opening an external OpenStreetMap map will disclose these "
                    +"coordinates to the chosen browser or map provider. Accubook itself "
                    +"does not connect to OpenStreetMap. Continue?")
                .setNegativeButton("Keep private",(d,w)->{})
                .setPositiveButton("Open externally",(d,w)->{
                    String lat=point.latitude,lon=point.longitude;
                    Uri url=Uri.parse("https://www.openstreetmap.org/?mlat="+lat+
                        "&mlon="+lon+"#map=16/"+lat+"/"+lon);
                    try{startActivity(new Intent(Intent.ACTION_VIEW,url));}
                    catch(Exception e){error(e);}
                }).show();
        }catch(Exception e){error(e);}
    }
    private void exportRoute(WorkspaceStore.Job job){
        pendingRouteExportId=job.id;
        Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        save.setType("application/gpx+xml");
        save.addCategory(Intent.CATEGORY_OPENABLE);
        save.putExtra(Intent.EXTRA_TITLE,"accubook-"+job.date+".gpx");
        try{startActivityForResult(save,ROUTE_EXPORT_REQUEST);}
        catch(Exception e){error(e);}
    }
    private String asGpx(WorkspaceStore.Job job) throws IOException{
        StringBuilder result=new StringBuilder(
            "<?xml version='1.0' encoding='UTF-8'?>\\n"+
            "<gpx version='1.1' creator='Accubook' xmlns='http://www.topografix.com/GPX/1/1'><trk><name>Private job route</name><trkseg>");
        for(CrmWorkspace.RoutePoint point:crm.routePoints(job)){
            result.append("<trkpt lat='").append(point.latitude).append("' lon='")
                .append(point.longitude).append("'><time>").append(point.at)
                .append("</time></trkpt>");
        }
        return result.append("</trkseg></trk></gpx>").toString();
    }

    private void createTestBusiness() {
        new AlertDialog.Builder(this).setTitle("Load fictional test company?")
            .setMessage("Creates a fictional example contracting business, three demo customers, "
                +"three jobs, appointment times, sample charges and sample payment-method entries. "
                +"Existing records are not replaced. Never use this data for real accounting.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Create sample",(d,w)->{
                try {
                    // Never overwrite an owner's business identity when seeding fake data.
                    // Demo customers and jobs are always labeled DEMO.
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
                            +"photographs and issue a estimate before work.");
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
                        + "Reschedule it, attach a test photo, and preview the invoice.");
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
            String greeting=LocalTime.now().getHour()<12?"Good morning":
                LocalTime.now().getHour()<17?"Good afternoon":"Good evening";
            screen("Accubook · Dashboard",greeting+
                "  |  PRIVATE • OFFLINE • YOUR DATA");
            navigation();
            button(content,"Find anything · name, phone, address, job, invoice",this::universalSearchScreen);
            section("Today · live overview");
            int todayJobs=0,upcomingJobs=0,sentQuotes=0,active=0;
            BigDecimal openDraft=BigDecimal.ZERO,paid=BigDecimal.ZERO;
            for(WorkspaceStore.Job entry:jobs){
                if(entry.date.equals(LocalDate.now().toString()))todayJobs++;
                if(entry.date.compareTo(LocalDate.now().toString())>=0)upcomingJobs++;
                if(entry.status.equals("Scheduled")||entry.status.equals("In Progress"))active++;
                if(crm.quote(entry).sent)sentQuotes++;
                openDraft=openDraft.add(new BigDecimal(entry.total));
                paid=paid.add(crm.received(entry));
            }
            LinearLayout summary=card();
            label(summary,"TODAY  "+LocalDate.now().getDayOfWeek()+" · "+
                LocalDate.now(),15,MUTED);
            label(summary,todayJobs+" appointments today   ·   "+upcomingJobs+
                " upcoming",21,LIGHT);
            label(summary,active+" active jobs   ·   "+customers.size()+
                " customers",17,LIGHT);
            label(summary,new ContactDirectory(store).all().size()+
                " saved contacts   ·   "+sentQuotes+" estimates sent",16,MUTED);
            label(summary,"JOB VALUE   $"+openDraft.toPlainString(),19,LIGHT);
            label(summary,"RECEIVED   $"+paid.toPlainString()+"   ·   OPEN   $"+
                openDraft.subtract(paid).toPlainString(),16,LIGHT);
            WorkspaceStore.Job next=null;
            for(WorkspaceStore.Job j:jobs)
                if(j.date.compareTo(LocalDate.now().toString())>=0 &&
                    (next==null||j.date.compareTo(next.date)<0))
                    next=j;
            if(next!=null){
                CrmWorkspace.Appointment time=crm.appointment(next);
                LinearLayout upcoming=card();
                label(upcoming,"NEXT VISIT",14,MUTED);
                label(upcoming,next.title,20,LIGHT);
                label(upcoming,next.date+"  ·  "+time.start+"–"+time.end,17,LIGHT);
                final String nextJob=next.id;
                button(upcoming,"Open next job →",()->job(nextJob));
            }
            button(content,"? How to use Accubook",this::helpScreen);
            if(FeatureSettings.enabled(this,FeatureSettings.RECURRING)){
                int due=0;
                for(RecurringServices.Rule reminder:new RecurringServices(store).all())
                    if(reminder.dueToday())due++;
                Button reminders=button(content,
                    due+" repeat services due by date · Open due list",this::serviceDueScreen);
                reminders.setBackgroundTintList(ColorStateList.valueOf(due>0?0xFF9A6825:CARD));
            }
            section("Quick actions");
            button(content,"＋ New scheduled job",this::chooseCustomer);
            button(content,"Calendar · look ahead",this::calendarScreen);
            button(content,"Contacts · import all or browse",this::contactsScreen);
            button(content,"＋ New customer",this::customerDialog);
            button(content,"Customize job checklist",this::masterJobTemplateScreen);
            button(content,"Try fictional sample job",this::createDemoWorkspace);

            button(content,"Open daybook schedule",this::scheduleScreen);
            button(content, "Export workspace ZIP backup", () -> {
                pendingBackup = true;
                pendingInvoice = null;
                document("accubook-workspace.zip", "application/zip");
            });
            button(content,"Create encrypted workspace backup",this::chooseEncryptedBackup);
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


    private void customerDialog() { customerDialog(null,"","",false); }

    private void customerDialog(WorkspaceStore.Customer existing,String selectedName,
                                String selectedPhone) {
        customerDialog(existing,selectedName,selectedPhone,false);
    }

    private void customerDialog(WorkspaceStore.Customer existing,String selectedName,
                                String selectedPhone,boolean createJobAfter) {
        try {
            CrmWorkspace.ContactPreferences prior=existing==null?
                new CrmWorkspace.ContactPreferences(java.util.Arrays.asList("true","false",
                    "true",CrmWorkspace.JOB_COLORS[0])):crm.preferences(existing);
            LinearLayout fields=form();
            EditText company=field(fields,"Company (optional)","Business name");
            EditText contact=field(fields,"Contact name (required)","First and last name");
            EditText phone=field(fields,"Phone","555-0000");
            phone.setInputType(InputType.TYPE_CLASS_PHONE);
            EditText email=field(fields,"Email","contact@example.com");
            email.setInputType(InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
            EditText street=field(fields,"Billing street","123 Main Street");
            EditText city=field(fields,"City","Boston");
            EditText region=field(fields,"State","MA");
            EditText zip=field(fields,"Postal code","02108");
            if(existing==null){
                contact.setText(selectedName);phone.setText(selectedPhone);
            }else{
                company.setText(existing.company);contact.setText(existing.contact);
                phone.setText(existing.phone);email.setText(existing.email);
                street.setText(existing.street);city.setText(existing.city);
                region.setText(existing.state);zip.setText(existing.zip);
            }
            label(fields,"Preferred contact methods · select any combination",16,LIGHT);
            CheckBox call=checkbox(fields,"Phone call",prior.call);
            CheckBox sms=checkbox(fields,"Text message (SMS)",prior.sms);
            CheckBox mail=checkbox(fields,"Email",prior.email);
            label(fields,"Preferences are contact choices, not marketing consent.",13,MUTED);
            String[] tint={prior.color};
            Button choose=button(fields,"Choose customer color",()->{});
            choose.setBackgroundTintList(ColorStateList.valueOf(Color.parseColor(tint[0])));
            choose.setOnClickListener(v->chooseJobColor(choose,tint));
            dialog(existing==null?"Create customer":"Edit customer",fields,()->{
                try{
                    WorkspaceStore.Customer saved=existing==null?
                        store.addCustomer(company.getText().toString(),contact.getText().toString(),
                            phone.getText().toString(),email.getText().toString(),
                            street.getText().toString(),city.getText().toString(),
                            region.getText().toString(),zip.getText().toString()):
                        store.updateCustomer(existing.id,company.getText().toString(),
                            contact.getText().toString(),phone.getText().toString(),
                            email.getText().toString(),street.getText().toString(),
                            city.getText().toString(),region.getText().toString(),
                            zip.getText().toString());
                    crm.savePreferences(saved,call.isChecked(),sms.isChecked(),mail.isChecked(),
                        tint[0]);
                    if(createJobAfter)jobDialog(saved);
                    else customer(saved.id);
                }catch(IOException e){throw new IllegalStateException(e);}
            });
        }catch(Exception e){error(e);}
    }

    private CheckBox checkbox(LinearLayout parent,String name,boolean checked) {
        CheckBox box=new CheckBox(this);
        box.setText(name);
        box.setTextColor(LIGHT);
        box.setTextSize(16);
        box.setChecked(checked);
        box.setMinHeight(dp(48));
        parent.addView(box,new LinearLayout.LayoutParams(-1,-2));
        return box;
    }

    private void chooseCustomer() {
        try {
            List<WorkspaceStore.Customer> customers=store.customers();
            String[] items=new String[customers.size()+1];
            items[0]="+ Create new customer and continue";
            for(int i=0;i<customers.size();i++)items[i+1]=customers.get(i).displayName();
            new AlertDialog.Builder(this).setTitle("Who is this job for?")
                .setItems(items,(dialog,index)->{
                    if(index==0)customerDialog(null,"","",true);
                    else jobDialog(customers.get(index-1));
                }).setNegativeButton("Cancel",(d,w)->{}).show();
        }catch(Exception e){error(e);}
    }

    private void jobDialog(WorkspaceStore.Customer customer) {
        LinearLayout fields=form();
        label(fields,"Customer: "+customer.displayName(),16,LIGHT);
        button(fields,"Change customer",this::chooseCustomer);
        button(fields,"Create another new customer",()->
            customerDialog(null,"","",true));
        EditText title=field(fields,"Job title (required)","Gutter cleaning");
        EditText street=field(fields,"Service street", "123 Main Street");
        street.setText(customer.street);
        EditText city=field(fields,"Service city", "Boston");
        city.setText(customer.city);
        EditText region=field(fields,"Service state", "MA");
        region.setText(customer.state);
        EditText zip=field(fields,"Service ZIP", "02108");
        zip.setText(customer.zip);
        label(fields,"Set appointment date and time (calendar or type)",16,LIGHT);
        EditText date=field(fields,"Date · YYYY-MM-DD","Tap calendar or enter a date");
        // No default scheduled date: the user explicitly chooses one.
        button(fields,"Choose date in calendar",()->openDate(date));
        EditText start=field(fields,"Start · 24-hour HH:mm","09:00");
        start.setText("09:00");
        button(fields,"Choose start with clock",()->openClock(start));
        EditText end=field(fields,"End · 24-hour HH:mm","10:00");
        end.setText("10:00");
        button(fields,"Choose end with clock",()->openClock(end));
        String[] tint={CrmWorkspace.JOB_COLORS[0]};
        try{tint[0]=crm.preferences(customer).color;}catch(Exception ignored){}
        Button chooseColor=button(fields,"Choose job color",()->{});
        chooseColor.setBackgroundTintList(ColorStateList.valueOf(Color.parseColor(tint[0])));
        chooseColor.setOnClickListener(v->chooseJobColor(chooseColor,tint));
        EditText notes=multiline(fields,"Appointment / daybook note","");
        dialog("New scheduled job",fields,()->{
            // Validate all user inputs BEFORE writing a customer-linked job.
            String iso=date.getText().toString().trim();
            try{LocalDate.parse(iso);}
            catch(Exception e){throw new IllegalArgumentException("Choose a date in the calendar or type YYYY-MM-DD");}
            LocalTime from,to;
            try{
                from=LocalTime.parse(start.getText().toString());
                to=LocalTime.parse(end.getText().toString());
            }catch(Exception e){throw new IllegalArgumentException("Choose valid start/end times");}
            if(!to.isAfter(from))throw new IllegalArgumentException("End time must be after start");
            try{
                WorkspaceStore.Job created=store.addJob(customer,title.getText().toString(),
                    street.getText().toString(),city.getText().toString(),
                    region.getText().toString(),zip.getText().toString(),iso);
                crm.saveAppointment(created,start.getText().toString(),end.getText().toString(),
                    tint[0],notes.getText().toString());
                job(created.id);
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }

    /**
     * One horizontally scrollable focus rail replaces the former multi-screen-
     * length job page. State stays attached to this job on section switches.
     */
    private void jobFocusTabs(WorkspaceStore.Job selected){
        List<String> ids=new ArrayList<>(java.util.Arrays.asList(
            "overview","photos","notes","materials","costing","checklists","schedule"));
        List<String> labels=new ArrayList<>(java.util.Arrays.asList(
            "Overview","Photos","Notes","Materials","Money","Checklist","Schedule"));
        if(FeatureSettings.enabled(this,FeatureSettings.WORKER_TIME)){
            ids.add("time");labels.add("Time");
        }
        if(FeatureSettings.enabled(this,FeatureSettings.GPS)){
            ids.add("route");labels.add("Route");
        }
        if(!ids.contains(currentJobSection))currentJobSection="overview";
        android.widget.HorizontalScrollView scroll=new android.widget.HorizontalScrollView(this);
        scroll.setHorizontalScrollBarEnabled(false);
        LinearLayout row=new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        scroll.addView(row);
        for(int i=0;i<ids.size();i++){
            final String id=ids.get(i);
            final String name=labels.get(i);
            boolean active=id.equals(currentJobSection);
            Button tab=new Button(this);
            tab.setText(name);
            tab.setAllCaps(false);
            tab.setTextSize(14);
            tab.setTextColor(LIGHT);
            tab.setMinHeight(dp(48));
            tab.setContentDescription(name+" job section"+
                (active?", selected":""));
            tab.setBackgroundTintList(ColorStateList.valueOf(active?ACCENT:CARD));
            LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-2,dp(48));
            params.setMargins(dp(3),dp(5),dp(3),dp(8));
            row.addView(tab,params);
            tab.setOnClickListener(v->{
                if(!id.equals(currentJobSection)){
                    currentJobSection=id;
                    job(selected.id);
                }
            });
        }
        content.addView(scroll,new LinearLayout.LayoutParams(-1,-2));
    }

    private void job(String id) {
        if(!id.equals(currentJobId)){
            currentJobSection="overview";currentPhotoPage=0;
        }
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
            jobFocusTabs(work);
            if("overview".equals(currentJobSection)){
            button(content, "Customer: " + client.displayName(), () -> customer(client.id));
            section("Job details");
            CrmWorkspace.Appointment appt=crm.appointment(work);
            label(content, "Scheduled: " + work.date + " · "+appt.start+"–"+appt.end,
                18, LIGHT);
            if(!appt.notes.isEmpty())label(content,"Daybook: "+appt.notes,16,MUTED);
            label(content, "Status: " + work.status, 17, LIGHT);
            label(content, "Site: " + work.street + ", " + work.city + ", " + work.state
                + " " + work.zip, 16, LIGHT);
            button(content, "Reschedule / change time / color / daybook note",
                () -> scheduleEditor(work));
            button(content,"Add this job to Calendar app",()->addJobToCalendar(work));
            button(content, "Change job status", () -> statusPicker(work));
            if(FeatureSettings.enabled(this,FeatureSettings.RECURRING))
                button(content,"Set or update next service due date / mileage",
                    ()->serviceIntervalDialog(work,null));
            }
            if("notes".equals(currentJobSection)){
            section("Field notes and site instructions");
            String notes = store.fieldNotes(work);
            label(content, notes.isEmpty() ? "No field notes yet."
                : (notes.length() > 800 ? notes.substring(0, 800) + "…" : notes),
                15, MUTED);
            button(content, "Edit field notes", () -> fieldNotesDialog(work));
            if(!notes.trim().isEmpty())
                button(content,"Use this note in a new invoice line",
                    ()->lineDialog(work,invoiceDescriptionFromNotes(notes)));
            }
            if("checklists".equals(currentJobSection)){
                jobCustomFields(work);
            }
            if("materials".equals(currentJobSection)){
            section("Vendors and deliveries");
            button(content,FeatureSettings.enabled(this,FeatureSettings.CREW)?
                "Edit vendors, materials and crew":"Edit vendor / material delivery",
                ()->jobLogisticsDialog(work));
            TradeModules operations=new TradeModules(store);
            TradeModules.Logistics details=operations.logistics(work);
            label(content,"Vendor: "+details.vendor+" · Delivery: "+details.delivery,15,MUTED);
            if(FeatureSettings.enabled(this,FeatureSettings.CREW))
                label(content,"Crew: "+details.crew,15,MUTED);
            if(!details.notes.isEmpty())label(content,details.notes,15,LIGHT);
            button(content,"Create dumpster pickup calendar reminder",
                ()->createPickupReminder(work));
            button(content,"Schedule device-only dumpster pickup alert",
                ()->localPickupReminder(work));
            long pickupDue=PickupReminders.due(store,work);
            if(pickupDue>0)
                label(content,"Local pickup reminder: "+
                    java.time.Instant.ofEpochMilli(pickupDue).atZone(
                        java.time.ZoneId.systemDefault()),14,MUTED);
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
            }
            if("costing".equals(currentJobSection)){
            section("Estimate and invoice");
            CrmWorkspace.Quote quoteState=crm.quote(work);
            CheckBox sent=checkbox(content,"Estimate sent (manually confirmed)",quoteState.sent);
            if(quoteState.sent)label(content,"Marked sent: "+quoteState.sentDate,14,MUTED);
            sent.setOnClickListener(view->{
                boolean next=sent.isChecked();
                sent.setChecked(!next); // avoid changing display until persisted
                new AlertDialog.Builder(this)
                    .setTitle(next?"Confirm estimate sent?":"Mark estimate unsent?")
                    .setMessage(next?"Only check this after you actually deliver the estimate.":
                        "Remove the manual sent flag? This does not retract a delivered message.")
                    .setNegativeButton("Cancel",(d,w)->{})
                    .setPositiveButton("Confirm",(d,w)->{
                        try{
                            crm.setQuoteSent(work,next,"Owner confirmed");
                            sent.setChecked(next);
                        }catch(Exception e){error(e);}
                    }).show();
            });
            button(content,"Preview / edit estimate (print or Save as PDF)",
                ()->openDocument(work,true));
            button(content,"Preview / edit invoice (print or Save as PDF)",
                ()->openDocument(work,false));
            label(content,"Job total: $"+work.total,22,LIGHT);
            if(FeatureSettings.enabled(this,FeatureSettings.CATALOG))
                button(content,"+ Add from service / consumable catalog",
                    ()->catalogLineDialog(work));
            button(content,"Add labor, material or discount",()->lineDialog(work));
            section("Linked change orders");
            button(content,"＋ New change order",()->changeOrderCreateDialog(work));
            for(ChangeOrders.Order change:new ChangeOrders(store).orders(work)){
                LinearLayout changeCard=card();
                label(changeCard,change.title+" · "+change.status,17,LIGHT);
                label(changeCard,"Amount change: $"+
                    new ChangeOrders(store).total(work,change),15,MUTED);
                button(changeCard,"View / manage change order",()->
                    changeOrderActions(work,change));
            }
            button(content,"Export invoice as HTML",()->{
                try{
                    pendingInvoice=InvoiceHtml.render(client,work,store.items(work));
                    pendingBackup=false;
                    document(DocumentNumbers.reference(work.id,work.date,false)+".html","text/html");
                }catch(Exception failure){error(failure);}
            });
            List<WorkspaceStore.LineItem> billLines=store.items(work);
            for(int i=0;i<billLines.size();i++){
                WorkspaceStore.LineItem item=billLines.get(i);
                LinearLayout row=card();
                LinearLayout header=new LinearLayout(this);
                header.setOrientation(LinearLayout.HORIZONTAL);
                row.addView(header);
                TextView title=label(header,item.description,17,LIGHT);
                title.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
                final int lineIndex=i;
                Runnable actions=()->invoiceLineActionMenu(work,item,lineIndex,
                    billLines.size());
                fieldMoreButton(header,"invoice line "+item.description,actions);
                label(row,item.quantity+" × $"+item.unitRate+" = $"+item.amount,14,MUTED);
                row.setOnLongClickListener(v->{actions.run();return true;});
                title.setOnLongClickListener(v->{actions.run();return true;});
            }
            }
            if("photos".equals(currentJobSection)){
            section("Job photos");
            button(content, "Add photo from device", () -> pickPhoto(work));
            button(content, "Import multiple photos",()->pickAttachments(work,true));
            List<String> photoNames=store.photos(work);
            final int pageSize=16;
            int pageCount=Math.max(1,(photoNames.size()+pageSize-1)/pageSize);
            currentPhotoPage=Math.min(Math.max(currentPhotoPage,0),pageCount-1);
            int start=currentPhotoPage*pageSize;
            int end=Math.min(photoNames.size(),start+pageSize);
            if(photoNames.isEmpty())
                label(content,"No photos attached. Tap Import multiple photos.",15,MUTED);
            else{
                label(content,"Photos "+(start+1)+"–"+end+" of "+photoNames.size()+
                    " · tap to view, ⋮ for actions or drag",14,MUTED);
                for(int n=start;n<end;n+=2){
                    LinearLayout row=new LinearLayout(this);
                    row.setOrientation(LinearLayout.HORIZONTAL);
                    content.addView(row,new LinearLayout.LayoutParams(-1,-2));
                    photoTile(row,work,photoNames.get(n),n+1,photoNames.size());
                    if(n+1<end)photoTile(row,work,photoNames.get(n+1),n+2,
                        photoNames.size());
                    else{
                        View spacer=new View(this);
                        row.addView(spacer,new LinearLayout.LayoutParams(0,dp(1),1));
                    }
                }
                if(pageCount>1){
                    label(content,"Page "+(currentPhotoPage+1)+" of "+pageCount,14,MUTED);
                    if(currentPhotoPage>0)button(content,"← Previous 16 photos",()->{
                        currentPhotoPage--;job(work.id);
                    });
                    if(currentPhotoPage<pageCount-1)
                        button(content,"Next 16 photos →",()->{
                            currentPhotoPage++;job(work.id);
                        });
                }
            }
            attachmentList(work);
            }
            if("costing".equals(currentJobSection)){
            section("Payment ledger");
            label(content,"Payments recorded: $"+crm.received(work).toPlainString(),17,LIGHT);
            label(content,"Open job balance: $"+crm.balance(work).toPlainString(),17,LIGHT);
            button(content,"Record cash, check, PayPal or other payment",()->paymentDialog(work));
            for(CrmWorkspace.Payment payment:crm.payments(work)){
                LinearLayout row=card();
                label(row,payment.date+" · "+payment.method+" · $"+payment.amount,16,LIGHT);
                label(row,"Reference: "+payment.reference+" · "+payment.note,14,MUTED);
            }
            }
            if("time".equals(currentJobSection) &&
                    FeatureSettings.enabled(this,FeatureSettings.WORKER_TIME)){
            section("Worker time tracking");
            label(content,"Recorded hours: "+crm.totalHours(work).toPlainString(),18,LIGHT);
            button(content,"Clock in a worker",()->clockInDialog(work));
            for(CrmWorkspace.TimeEntry entry:crm.timeEntries(work)){
                LinearLayout clock=card();
                label(clock,entry.worker+" · "+entry.start,16,LIGHT);
                label(clock,entry.active()?"Clocked in now":
                    "Clocked out "+entry.end+" · "+entry.hours+" hours",15,MUTED);
                if(entry.active())button(clock,"Clock out "+entry.worker,
                    ()->clockOutConfirm(work,entry));
            }
            }
            if("route".equals(currentJobSection) &&
                    FeatureSettings.enabled(this,FeatureSettings.GPS)){
            section("Private route / geolocation");
            List<CrmWorkspace.RoutePoint> route=crm.routePoints(work);
            label(content,route.size()+" GPS points stored locally. Tracking stops when "
                +"you leave the app.",14,MUTED);
            button(content,routeListener!=null?"Stop GPS tracking":
                "Start optional GPS route tracking",()->toggleRoute(work));
            if(!route.isEmpty()){
                button(content,"Export private route as GPX",()->exportRoute(work));
                button(content,"Open last point in OpenStreetMap (shares coordinates)",
                    ()->openRouteInOSM(work));
            }
            }
            if("schedule".equals(currentJobSection)){
                section("Calendar and scheduling");
                CrmWorkspace.Appointment schedule=crm.appointment(work);
                label(content,work.date+" · "+schedule.start+"–"+schedule.end,18,LIGHT);
                label(content,schedule.notes.isEmpty()?"No daybook notes":schedule.notes,15,MUTED);
                button(content,"Reschedule / adjust job color or time",
                    ()->scheduleEditor(work));
                button(content,"Add this job to Calendar app",()->addJobToCalendar(work));
            }
            if("costing".equals(currentJobSection))
                label(content,"Offline manual records only. No payment collection, tax "
                    +"calculation or settlement verification occurs.",13,MUTED);
        } catch (Exception failure) { error(failure); }
    }


    private void invoiceLineActionMenu(WorkspaceStore.Job job,
            WorkspaceStore.LineItem line,int index,int count){
        boolean approved=line.description.matches("(?s).*\\[CO:COL-[a-f0-9]{32}\\]$");
        List<String> actions=new ArrayList<>();
        if(index>0)actions.add("Move up");
        if(index<count-1)actions.add("Move down");
        if(!approved){
            actions.add("Change quantity +1");
            actions.add("Change quantity -1");
            actions.add("Edit line");
            actions.add("Remove line");
        }else actions.add("Approved change-order lines are locked");
        new AlertDialog.Builder(this).setTitle(line.description)
            .setItems(actions.toArray(new String[0]),(d,which)->{
                String selected=actions.get(which);
                try{
                    switch(selected){
                        case "Move up":
                            store.moveLine(job,line.id,index-1);job(job.id);break;
                        case "Move down":
                            store.moveLine(job,line.id,index+1);job(job.id);break;
                        case "Change quantity +1":changeLineQuantity(job,line,1);break;
                        case "Change quantity -1":changeLineQuantity(job,line,-1);break;
                        case "Edit line":editLineDialog(job,line);break;
                        case "Remove line":deleteLine(job,line);break;
                        default:notice("Change-order protection",
                            "Approved work is immutable. Create a correcting change order.");
                    }
                }catch(Exception e){error(e);}
            }).setNegativeButton("Cancel",(d,w)->{}).show();
    }

    private void changeLineQuantity(WorkspaceStore.Job job,WorkspaceStore.LineItem line,int change){
        try {
            BigDecimal next=new BigDecimal(line.quantity).add(BigDecimal.valueOf(change));
            if(next.signum()<=0){
                notice("Quantity minimum","Quantity cannot be zero. Use Remove for deletion.");
                return;
            }
            new AlertDialog.Builder(this).setTitle("Confirm billing change")
                .setMessage(line.description+": "+line.quantity+" → "+next.toPlainString()
                    +" at $"+line.unitRate+" per unit. Update this billing line?")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton("Update",(d,w)->{
                    try{
                        store.updateLine(job,line.id,line.description,next.toPlainString(),
                            line.unitRate);
                        job(job.id);
                    }catch(Exception e){error(e);}
                }).show();
        }catch(Exception e){error(e);}
    }

    /** Field-ready catalog selection inserts a canonical invoice line immediately. */
    private void catalogLineDialog(WorkspaceStore.Job job){
        try{
            TradeModules trade=new TradeModules(store);
            List<TradeModules.CatalogItem> items=trade.catalog();
            String[] options=new String[items.size()+1];
            for(int i=0;i<items.size();i++)options[i]=items.get(i).label();
            options[items.size()]="+ Manage catalog items and prices";
            new AlertDialog.Builder(this).setTitle("Choose service or consumable")
                .setItems(options,(d,index)->{
                    if(index==items.size()){catalogScreen();return;}
                    TradeModules.CatalogItem item=items.get(index);
                    LinearLayout fields=form();
                    label(fields,item.category+" · "+item.name+" · "+item.unit,17,LIGHT);
                    EditText quantity=field(fields,"Quantity","1");
                    quantity.setText("1");
                    quantity.setInputType(InputType.TYPE_CLASS_NUMBER|
                        InputType.TYPE_NUMBER_FLAG_DECIMAL);
                    EditText markup=field(fields,"Markup % (this job only)",item.markup);
                    markup.setText(item.markup);
                    markup.setInputType(InputType.TYPE_CLASS_NUMBER|
                        InputType.TYPE_NUMBER_FLAG_DECIMAL|
                        InputType.TYPE_NUMBER_FLAG_SIGNED);
                    EditText description=field(fields,"Description on invoice",item.name);
                    description.setText(item.name);
                    label(fields,"Base cost: $"+item.cost+" · Default sell price: $"+item.price(),
                        15,MUTED);
                    button(fields,"Preview calculated sell rate",()->{
                        try{
                            BigDecimal rate=PricingEngine.price(new BigDecimal(item.cost),
                                new BigDecimal(markup.getText().toString()));
                            notice("Preview",description.getText().toString()+" · $"+
                                rate.toPlainString()+" per "+item.unit+
                                " · extended $"+PricingEngine.extended(
                                    new BigDecimal(quantity.getText().toString()),rate));
                        }catch(Exception e){error(e);}
                    });
                    dialog("Add catalog item to invoice",fields,()->{
                        BigDecimal rate=PricingEngine.price(new BigDecimal(item.cost),
                            new BigDecimal(markup.getText().toString()));
                        try{
                            store.addLine(job,description.getText().toString(),
                                quantity.getText().toString(),rate.toPlainString());
                            job(job.id);
                        }catch(IOException e){throw new IllegalStateException(e);}
                    });
                }).setNegativeButton("Cancel",(d,index)->{}).show();
        }catch(Exception e){error(e);}
    }
    private void catalogScreen(){
        currentScreen="catalog";
        currentJobId=null;
        currentCustomerId=null;
        try{
            screen("Services and consumables",
                "Editable business-wide items · prices are examples, not supplier quotes");
            navigation();
            button(content,"+ Add service or material",()->catalogEdit(null));
            button(content,"Import supplier price-sheet CSV",this::pickSupplierSheet);
            label(content,"Supplier APIs require business access. This importer accepts "
                +"an owner-approved CSV (no background network requests) and records "
                +"the source and price timestamp.",14,MUTED);
            label(content,"Catalog changes affect future line items only. Existing estimates "
                +"and invoices retain the rates you approved.",14,MUTED);
            for(TradeModules.CatalogItem item:new TradeModules(store).catalog()){
                LinearLayout row=card();
                label(row,item.name+" · "+item.category,18,LIGHT);
                label(row,"Unit: "+item.unit+" · base cost $"+item.cost+
                    " · markup "+item.markup+"% · sell $"+item.price(),15,MUTED);
                label(row,"Supplier: "+item.supplier,13,MUTED);
                button(row,"Edit item or markup",()->catalogEdit(item));
            }
        }catch(Exception e){error(e);}
    }
    private void pickSupplierSheet(){
        new AlertDialog.Builder(this).setTitle("Import supplier prices?")
            .setMessage("Import a CSV you obtained from Lansing, QXO, SRS Distribution "
                +"or a manual source. Validate the source and prices before using them "
                +"on customer estimates. This does not connect to a supplier account. "
                +"Expected columns: Supplier,SKU,Name,Unit,BaseCost,MarkupPercent,AsOfUTC.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Choose CSV",(d,w)->{
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);
                pick.setType("text/*");
                try{startActivityForResult(pick,SUPPLIER_CSV_REQUEST);}
                catch(Exception e){error(e);}
            }).show();
    }

    private void catalogEdit(TradeModules.CatalogItem existing){
        LinearLayout form=form();
        EditText category=field(form,"Category (any trade)","Gutter cleaning");
        EditText name=field(form,"Service / item name","Standard gutter cleaning");
        EditText unit=field(form,"Unit","service / each / linear foot / hour");
        EditText cost=field(form,"Baseline cost · USD","250.00");
        EditText markup=field(form,"Default markup %","0");
        EditText supplier=field(form,"Supplier or pricing source","Manual / Lansing / QXO / SRS");
        if(existing!=null){
            category.setText(existing.category);name.setText(existing.name);
            unit.setText(existing.unit);cost.setText(existing.cost);
            markup.setText(existing.markup);supplier.setText(existing.supplier);
        }
        dialog(existing==null?"New catalog item":"Edit catalog item",form,()->{
            try{
                new TradeModules(store).saveItem(existing==null?null:existing.id,
                    category.getText().toString(),name.getText().toString(),
                    unit.getText().toString(),cost.getText().toString(),
                    markup.getText().toString(),supplier.getText().toString());
                catalogScreen();
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }
    /** Compact visible overflow, with the same actions available on long-press. */
    private void fieldMoreButton(LinearLayout parent,String label,Runnable action){
        Button more=new Button(this);
        more.setText("\u22ee");
        more.setTextSize(24);
        more.setAllCaps(false);
        more.setContentDescription("Actions for "+label);
        more.setTextColor(LIGHT);
        more.setBackground(box(CARD));
        more.setMinWidth(dp(48));
        more.setMinHeight(dp(48));
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(dp(52),dp(52));
        parent.addView(more,params);
        more.setOnClickListener(v->action.run());
    }
    private void fieldActionMenu(JobTemplates.Field selected,WorkspaceStore.Job job,
                                 int index,int length){
        boolean master=job==null;
        List<String> options=new ArrayList<>();
        options.add("Edit field");
        if(index>0)options.add("Move up");
        if(index<length-1)options.add("Move down");
        options.add(selected.required?"Make optional":"Set required");
        options.add("Remove");
        new AlertDialog.Builder(this).setTitle(selected.label)
            .setItems(options.toArray(new String[0]),(dialog,which)->{
                String choice=options.get(which);
                try{
                    JobTemplates forms=new JobTemplates(store);
                    if(choice.equals("Edit field")){
                        if(master)editMasterField(selected);else editJobField(job,selected);
                        return;
                    }
                    if(choice.equals("Remove")){
                        new AlertDialog.Builder(this).setTitle("Remove field?")
                            .setMessage(master?"Remove from future job templates? Existing "
                                +"job values will remain.":"Remove from this job only? "
                                +"Master template and other jobs will remain unchanged.")
                            .setNegativeButton("Cancel",(d,w)->{})
                            .setPositiveButton("Remove",(d,w)->{
                                try{
                                    if(master)forms.removeMaster(selected.id);
                                    else forms.removeJob(job,selected.id);
                                    if(master)masterJobTemplateScreen();else job(job.id);
                                }catch(Exception error){error(error);}
                            }).show();
                        return;
                    }
                    if(choice.equals("Move up")||choice.equals("Move down")){
                        int next=index+(choice.equals("Move up")?-1:1);
                        if(master)forms.moveMaster(selected.id,next);
                        else forms.moveJob(job,selected.id,next);
                    }else{
                        if(master)forms.saveMaster(selected.id,selected.label,selected.kind,
                            !selected.required,selected.value);
                        else forms.saveJob(job,selected.id,selected.label,selected.kind,
                            !selected.required,selected.value);
                    }
                    if(master)masterJobTemplateScreen();else job(job.id);
                }catch(Exception error){error(error);}
            }).setNegativeButton("Cancel",(d,w)->{}).show();
    }
    private void masterJobTemplateScreen(){
        currentScreen="job_template";currentCustomerId=null;currentJobId=null;
        try{
            screen("Master job template",
                "Reorder and customize fields for new jobs without changing existing work");
            navigation();
            label(content,"Long-press a field or use its three-dot menu to edit, reorder, "
                +"set required or remove it. Existing job data is never overwritten.",
                15,MUTED);
            button(content,"+ Add template field",()->editMasterField(null));
            List<JobTemplates.Field> fields=new JobTemplates(store).master();
            for(int i=0;i<fields.size();i++){
                JobTemplates.Field field=fields.get(i);
                final int position=i;
                LinearLayout entry=card();
                LinearLayout header=new LinearLayout(this);
                header.setOrientation(LinearLayout.HORIZONTAL);
                entry.addView(header,new LinearLayout.LayoutParams(-1,-2));
                TextView title=label(header,field.label,18,LIGHT);
                title.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
                Runnable actions=()->fieldActionMenu(field,null,position,fields.size());
                fieldMoreButton(header,field.label,actions);
                label(entry,field.kind+" · "+(field.required?"Required":"Optional")+
                    (field.value.isEmpty()?"":" · Default: "+field.value),14,MUTED);
                entry.setOnLongClickListener(v->{actions.run();return true;});
                title.setOnLongClickListener(v->{actions.run();return true;});
            }
        }catch(Exception error){error(error);}
    }
    /** Type-specific editor: no user must enter true/false for a checkbox. */
    private static String customFieldValue(String kind,CheckBox checked,
        EditText text,EditText date,EditText number){
        if(kind.equals(JobTemplates.CHECK))return Boolean.toString(checked.isChecked());
        if(kind.equals(JobTemplates.DATE))return date.getText().toString();
        if(kind.equals(JobTemplates.NUMBER))return number.getText().toString();
        return text.getText().toString();
    }
    private void customFieldEditor(JobTemplates.Field old,WorkspaceStore.Job job){
        boolean master=job==null;
        LinearLayout fields=form();
        EditText name=field(fields,"Field name · you can rename it","Site visit confirmed");
        if(old!=null)name.setText(old.label);
        String[] kind={old==null?JobTemplates.CHECK:old.kind};
        Button type=button(fields,"Field type: "+kind[0],()->{});
        CheckBox required=checkbox(fields,"Required before a job can be completed",
            old!=null&&old.required);
        CheckBox checked=checkbox(fields,"Completed / checked",
            old!=null&&old.kind.equals(JobTemplates.CHECK)&&old.checked());
        EditText text=multiline(fields,master?"Default text or instructions":
            "Job-specific notes or value",
            old!=null&&old.kind.equals(JobTemplates.TEXT)?old.value:"");
        EditText date=field(fields,"Date (tap calendar or type YYYY-MM-DD)","YYYY-MM-DD");
        if(old!=null&&old.kind.equals(JobTemplates.DATE))date.setText(old.value);
        Button datePicker=button(fields,"Pick date",()->openDate(date));
        EditText number=field(fields,"Number","0");
        number.setInputType(InputType.TYPE_CLASS_NUMBER|
            InputType.TYPE_NUMBER_FLAG_DECIMAL|InputType.TYPE_NUMBER_FLAG_SIGNED);
        if(old!=null&&old.kind.equals(JobTemplates.NUMBER))number.setText(old.value);
        Runnable show=()->{
            checked.setVisibility(kind[0].equals(JobTemplates.CHECK)?View.VISIBLE:View.GONE);
            text.setVisibility(kind[0].equals(JobTemplates.TEXT)?View.VISIBLE:View.GONE);
            date.setVisibility(kind[0].equals(JobTemplates.DATE)?View.VISIBLE:View.GONE);
            datePicker.setVisibility(kind[0].equals(JobTemplates.DATE)?View.VISIBLE:View.GONE);
            number.setVisibility(kind[0].equals(JobTemplates.NUMBER)?View.VISIBLE:View.GONE);
        };
        show.run();
        type.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("Choose field type")
            .setItems(JobTemplates.KINDS,(d,index)->{
                kind[0]=JobTemplates.KINDS[index];
                type.setText("Field type: "+kind[0]);show.run();
            }).show());
        dialog(master?(old==null?"Add to master template":"Edit master template field"):
            (old==null?"New job field":"Edit job field"),fields,()->{
            String value=customFieldValue(kind[0],checked,text,date,number);
            try {
                JobTemplates templates=new JobTemplates(store);
                if(master){
                    templates.saveMaster(old==null?null:old.id,name.getText().toString(),
                        kind[0],required.isChecked(),value);
                    masterJobTemplateScreen();
                }else{
                    templates.saveJob(job,old==null?null:old.id,name.getText().toString(),
                        kind[0],required.isChecked(),value);
                    job(job.id);
                }
            }catch(IOException failure){throw new IllegalStateException(failure);}
        });
    }
    private void editMasterField(JobTemplates.Field old){customFieldEditor(old,null);}
    private void editJobField(WorkspaceStore.Job job,JobTemplates.Field old){
        customFieldEditor(old,job);
    }

    private void jobCustomFields(WorkspaceStore.Job work)throws IOException{
        section("Custom checklist and fields");
        button(content,"+ Add a field or checklist item",()->editJobField(work,null));
        button(content,"Edit master template (future jobs)",this::masterJobTemplateScreen);
        List<JobTemplates.Field> fields=new JobTemplates(store).forJob(work);
        for(int i=0;i<fields.size();i++){
            JobTemplates.Field f=fields.get(i);
            final int position=i;
            LinearLayout row=card();
            LinearLayout header=new LinearLayout(this);
            header.setOrientation(LinearLayout.HORIZONTAL);
            row.addView(header,new LinearLayout.LayoutParams(-1,-2));
            Runnable actions=()->fieldActionMenu(f,work,position,fields.size());
            if(f.kind.equals(JobTemplates.CHECK)){
                CheckBox check=checkbox(header,f.label+
                    (f.required?" · Required":""),f.checked());
                check.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
                check.setOnClickListener(v->{
                    boolean next=check.isChecked();
                    try{
                        new JobTemplates(store).saveJob(work,f.id,f.label,f.kind,
                            f.required,Boolean.toString(next));
                        Toast.makeText(this,"Saved "+f.label,Toast.LENGTH_SHORT).show();
                    }catch(Exception error){
                        check.setChecked(!next);
                        error(error);
                    }
                });
            }else{
                TextView title=label(header,f.label+
                    (f.required?" · Required":""),17,LIGHT);
                title.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
                title.setOnLongClickListener(v->{actions.run();return true;});
                label(row,f.value.isEmpty()?"Not entered":f.value,15,MUTED);
            }
            fieldMoreButton(header,f.label,actions);
            row.setOnLongClickListener(v->{actions.run();return true;});
        }
        List<String> incomplete=new JobTemplates(store).missingRequired(work);
        if(!incomplete.isEmpty())
            label(content,"Required before completion: "+
                String.join(", ",incomplete),14,MUTED);
        button(content,"View previous-format milestone checklist",
            ()->legacyMilestonesScreen(work));
    }
    private void legacyMilestonesScreen(WorkspaceStore.Job job){
        currentScreen="job";currentJobId=job.id;
        try{
            screen("Previous milestone checklist",job.title+
                " · legacy checklist preserved for compatibility");
            navigation();
            button(content,"Return to job",()->job(job.id));
            button(content,"+ Add previous-format milestone",()->addJobMilestone(job));
            TradeModules operations=new TradeModules(store);
            for(TradeModules.Milestone step:operations.milestones(job)){
                LinearLayout row=card();
                label(row,(step.complete()?"✓ ":"□ ")+step.name,17,LIGHT);
                button(row,step.complete()?"Reopen":"Mark complete",
                    ()->toggleMilestone(job,step));
            }
        }catch(Exception e){error(e);}
    }

    private void jobLogisticsDialog(WorkspaceStore.Job job) {
        try{
            TradeModules.Logistics current=new TradeModules(store).logistics(job);
            LinearLayout fields=form();
            EditText vendor=field(fields,"Assigned dumpster/vendor company",
                "Vendor name / contact");
            vendor.setText(current.vendor);
            EditText delivery=field(fields,"Material delivery contact",
                "Supplier driver / manager");
            delivery.setText(current.delivery);
            EditText crew=null;
            if(FeatureSettings.enabled(this,FeatureSettings.CREW)){
                crew=field(fields,"Assigned crew or personnel","Crew names");
                crew.setText(current.crew);
            }
            final EditText chosenCrew=crew;
            EditText notes=multiline(fields,"Operations notes / site instructions",
                current.notes);
            dialog("Job vendors and logistics",fields,()->{
                try{
                    new TradeModules(store).saveLogistics(job,vendor.getText().toString(),
                        delivery.getText().toString(),
                        chosenCrew==null?current.crew:chosenCrew.getText().toString(),
                        notes.getText().toString());
                    job(job.id);
                }catch(IOException e){throw new IllegalStateException(e);}
            });
        }catch(Exception e){error(e);}
    }
    private void addJobMilestone(WorkspaceStore.Job job) {
        LinearLayout fields=form();
        EditText name=field(fields,"Milestone name","Customer approval, inspection...");
        dialog("Add custom job checklist item",fields,()->{
            try{
                new TradeModules(store).addMilestone(job,name.getText().toString());
                job(job.id);
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }
    private void toggleMilestone(WorkspaceStore.Job job,TradeModules.Milestone old) {
        boolean next=!old.complete();
        new AlertDialog.Builder(this).setTitle(next?"Mark milestone complete?":"Reopen milestone?")
            .setMessage(old.name+" — this change will be recorded in the local job log.")
            .setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Confirm",(d,w)->{
                try{
                    new TradeModules(store).setMilestone(job,old.key,next,old.notes);
                    job(job.id);
                    if(next&&old.name.toLowerCase(Locale.ROOT).contains("dumpster delivered"))
                        notice("Pickup reminder","Remember to schedule a dumpster pickup "
                            +"before closing the job. Add a calendar reminder from this job.");
                }catch(Exception e){error(e);}
            }).show();
    }


    private void changeOrderCreateDialog(WorkspaceStore.Job job){
        LinearLayout fields=form();
        EditText title=field(fields,"What changed?","Extra downspout, repair, added labor");
        label(fields,"Linked to this job. A change order is not a separate quote.",14,MUTED);
        dialog("New change order",fields,()->{
            try{
                ChangeOrders.Order made=new ChangeOrders(store).create(job,
                    title.getText().toString());
                changeOrderActions(job,made);
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }

    private void changeOrderActions(WorkspaceStore.Job job,ChangeOrders.Order order){
        try{
            ChangeOrders changes=new ChangeOrders(store);
            List<ChangeOrders.Line> entries=changes.lines(job,order);
            StringBuilder description=new StringBuilder();
            for(ChangeOrders.Line entry:entries)description.append("\n")
                .append(entry.description).append(" · ")
                .append(entry.quantity).append(" × $").append(entry.rate);
            String message="Status: "+order.status+"\nDelta: $"+changes.total(job,order)+
                "\n"+(order.signed()?"Acknowledged by "+order.signedBy+" on "+order.acknowledged+
                    "\nLocal SHA-256 proof verified.":"Customer has not signed.")+
                "\n\n"+(description.length()==0?"No lines yet.":description.toString());
            AlertDialog.Builder menu=new AlertDialog.Builder(this)
                .setTitle(order.title).setMessage(message)
                .setNegativeButton("Close",(d,w)->{
                    currentJobSection="costing";job(job.id);
                });
            if(ChangeOrders.PROPOSED.equals(order.status)){
                menu.setNeutralButton("＋ Add work",(d,w)->changeOrderLineDialog(job,order));
                if(!entries.isEmpty())menu.setPositiveButton("Sign / acknowledge",
                    (d,w)->changeOrderSignDialog(job,order));
            }else if(ChangeOrders.ACKNOWLEDGED.equals(order.status)){
                menu.setPositiveButton("Add to invoice",(d,w)->
                    new AlertDialog.Builder(this).setTitle("Confirm billing")
                        .setMessage("Add these approved work lines to the original job invoice? "+
                            "Each line is linked and added only once.")
                        .setNegativeButton("Cancel",(confirmDialog,which)->{})
                        .setPositiveButton("Add",(confirmDialog,which)->{
                            try{
                                changes.addToInvoice(job,order);
                                currentJobSection="costing";job(job.id);
                            }catch(Exception e){error(e);}
                        }).show());
            }
            menu.show();
        }catch(Exception e){error(e);}
    }

    private void changeOrderLineDialog(WorkspaceStore.Job job,ChangeOrders.Order order){
        LinearLayout fields=form();
        EditText desc=field(fields,"Work to add","Install additional downspout");
        EditText qty=field(fields,"Quantity","1");qty.setText("1");
        qty.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText rate=field(fields,"Unit rate","85.00");
        rate.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL|
            InputType.TYPE_NUMBER_FLAG_SIGNED);
        dialog("Add change-order work",fields,()->{
            try{
                new ChangeOrders(store).addLine(job,order,desc.getText().toString(),
                    qty.getText().toString(),rate.getText().toString());
                currentJobSection="costing";job(job.id);
            }catch(IOException e){throw new IllegalStateException(e);}
        });
    }

    private void changeOrderSignDialog(WorkspaceStore.Job job,ChangeOrders.Order order){
        try{
            ChangeOrders changes=new ChangeOrders(store);
            LinearLayout fields=form();
            label(fields,"CHANGE ORDER · "+order.title,18,LIGHT);
            label(fields,"Review these additional items and prices before signing. "+
                "This amount is added to the original job, not a second quotation.",15,MUTED);
            for(ChangeOrders.Line line:changes.lines(job,order))
                label(fields,line.description+"\n"+line.quantity+" × $"+line.rate+
                    " = $"+line.amount,16,LIGHT);
            label(fields,"Additional approved amount: $"+changes.total(job,order),
                19,LIGHT);
            CheckBox acknowledged=checkbox(fields,
                "I reviewed these added items and approve the additional amount",false);
            label(fields,"A finger/stylus image, signer name and timestamp are kept "+
                "locally with an integrity hash. The app cannot verify legal identity.",
                13,MUTED);
            EditText signer=field(fields,"Printed name of signer",
                "Customer or authorized person");
            SignaturePadView pad=new SignaturePadView(this);
            fields.addView(pad,new LinearLayout.LayoutParams(-1,dp(190)));
            button(fields,"Clear signature",pad::clear);
            dialog("Acknowledge change order",fields,()->{
                if(!acknowledged.isChecked())
                    throw new IllegalArgumentException(
                        "Review the work and check the acknowledgment before saving");
                try{
                    changes.acknowledge(job,order,signer.getText().toString(),pad.png());
                    currentJobSection="costing";job(job.id);
                }catch(IOException e){throw new IllegalStateException(e);}
            });
        }catch(Exception e){error(e);}
    }

    private static String invoiceDescriptionFromNotes(String notes){
        for(String line:notes.split("\\R")){
            String candidate=line.trim().replaceAll("\\s+"," ");
            if(candidate.length()>180)candidate=candidate.substring(0,180).trim();
            if(!candidate.isEmpty())return candidate;
        }
        return "Work described in field notes";
    }

    private void lineDialog(WorkspaceStore.Job job){lineDialog(job,"");}

    private void lineDialog(WorkspaceStore.Job job,String preset) {
        LinearLayout fields = form();
        EditText description = field(fields, "Description (required)", "4-inch gutter cleanout");
        EditText quantity = field(fields, "Quantity", "1");
        quantity.setText("1");
        quantity.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText rate = field(fields, "Unit rate · negative only for discount", "85.00");
        rate.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED |
            InputType.TYPE_NUMBER_FLAG_DECIMAL);
        if(FeatureSettings.enabled(this,FeatureSettings.CATALOG)){
            LinearLayout suggestions=new LinearLayout(this);
            suggestions.setOrientation(LinearLayout.VERTICAL);
            fields.addView(suggestions);
            label(fields,"Suggestions are optional. Your own wording and prices always work.",
                13,MUTED);
            description.addTextChangedListener(new TextWatcher(){
                public void beforeTextChanged(CharSequence s,int st,int count,int after){}
                public void onTextChanged(CharSequence s,int st,int before,int count){
                    suggestions.removeAllViews();
                    try{
                        List<TradeModules.CatalogItem> catalog=new TradeModules(store).catalog();
                        catalog.sort((a,b)->Integer.compare(
                            CatalogSuggestions.score(s.toString(),b.name,b.category),
                            CatalogSuggestions.score(s.toString(),a.name,a.category)));
                        int shown=0;
                        for(TradeModules.CatalogItem item:catalog){
                            if(CatalogSuggestions.score(s.toString(),item.name,item.category)<=0)
                                continue;
                            button(suggestions,"Use "+item.name+" · $"+item.price(),()->{
                                description.setText(item.name);
                                description.setSelection(description.length());
                                rate.setText(item.price());
                            });
                            if(++shown>=3)break;
                        }
                    }catch(Exception ignored){} // Free text must remain usable.
                }
                public void afterTextChanged(Editable e){}
            });
        }
        if(!preset.isEmpty()){
            description.setText(preset);
            description.setSelection(description.length());
        }
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
        if(requestCode==BUSINESS_SETUP_REQUEST){
            if(resultCode==RESULT_OK && store!=null)home();
            return;
        }
        if(requestCode==UNLOCK_REQUEST){
            lockRequestInProgress=false;
            if(resultCode==RESULT_OK){
                unlocked=true;
                if(store==null)initializeWorkspace(restoreAfterUnlock);
                else home();
                restoreAfterUnlock=null;
            }else{
                unlocked=false;
                lockedScreen();
            }
            return;
        }
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
        if(requestCode==ENCRYPTED_BACKUP_EXPORT){
            char[] pass=pendingBackupPassword;
            pendingBackupPassword=null;
            if(pass==null)return;
            if(resultCode==RESULT_OK&&data!=null&&data.getData()!=null)
                encryptWorkspace(data.getData(),pass);
            else java.util.Arrays.fill(pass,'\0');
            return;
        }
        if(requestCode==ENCRYPTED_BACKUP_IMPORT){
            if(resultCode!=RESULT_OK||data==null||data.getData()==null)return;
            Uri selected=data.getData();
            backupPasswordDialog("Unlock encrypted backup",false,
                pass->decryptWorkspace(selected,pass));
            return;
        }
        if(requestCode==SUPPLIER_CSV_REQUEST){
            if(resultCode!=RESULT_OK||data==null||data.getData()==null)return;
            try(InputStream in=getContentResolver().openInputStream(data.getData())){
                int count=new TradeModules(store).importSupplierCsv(in);
                catalogScreen();
                notice("Supplier price sheet imported",count+" new catalog items saved. "
                    +"Review the markup before billing customers.");
            }catch(Exception e){error(e);}
            return;
        }

        if(requestCode==SERVICE_SLIP_PDF_REQUEST){
            if(resultCode!=RESULT_OK||data==null||data.getData()==null)return;
            try(OutputStream out=getContentResolver().openOutputStream(data.getData(),"wt")){
                if(out==null)throw new IOException("Cannot open selected PDF destination");
                List<RecurringServices.Rule> due=new ArrayList<>();
                for(RecurringServices.Rule rule:new RecurringServices(store).all())
                    if(rule.dueToday())due.add(rule);
                if(due.isEmpty())throw new IOException(
                    "There are no date-due services to print. No file was generated.");
                java.util.Map<String,WorkspaceStore.Customer> byId=
                    new java.util.HashMap<>();
                for(WorkspaceStore.Customer customer:store.customers())
                    byId.put(customer.id,customer);
                ServiceDuePdf.write(crm.branding().business,due,byId,out);
                notice("Due slips saved","PDF written to your chosen destination. "+
                    "No customers were contacted automatically.");
            }catch(Exception failure){error(failure);}
            return;
        }
        if(requestCode==REPORT_EXPORT_REQUEST){
            boolean[] sections=pendingReportSections;
            String[] methods=pendingReportMethods,categories=pendingReportCategories;
            boolean pdf=pendingReportPdf;
            pendingReportSections=null;
            pendingReportMethods=null;
            pendingReportCategories=null;
            pendingReportPdf=false;
            if(resultCode!=RESULT_OK||data==null||data.getData()==null)return;
            if(sections==null||methods==null||categories==null){
                error(new IOException("Report selection expired; please try again"));return;
            }
            try(OutputStream out=getContentResolver().openOutputStream(data.getData(),"wt")){
                if(out==null)throw new IOException("Cannot open report destination");
                ReportSelection selection=new ReportSelection(sections,
                    new java.util.LinkedHashSet<>(java.util.Arrays.asList(methods)),
                    new java.util.LinkedHashSet<>(java.util.Arrays.asList(categories)));
                if(pdf)QuickReportPdf.write(BusinessReports.summary(store,crm,selection),out);
                else BusinessReports.export(store,crm,selection,out);
                notice("Report saved",pdf?"Local PDF summary saved to your chosen file.":
                    "Selected CSV ZIP saved. Review its README before importing into "
                        +"accounting software.");
            }catch(Exception e){error(e);}
            return;
        }
        if(requestCode==ROUTE_EXPORT_REQUEST){
            String jobId=pendingRouteExportId;
            pendingRouteExportId=null;
            if(resultCode!=RESULT_OK||data==null||data.getData()==null||jobId==null)return;
            try(OutputStream out=getContentResolver().openOutputStream(data.getData(),"wt")){
                if(out==null)throw new IOException("Cannot write GPX");
                out.write(asGpx(jobById(jobId)).getBytes(StandardCharsets.UTF_8));
                out.flush();
                notice("GPX exported","A locally recorded route was exported to your chosen file.");
            }catch(Exception e){error(e);}
            return;
        }
        if (requestCode == LOGO_REQUEST) {
            if(resultCode!=RESULT_OK||data==null||data.getData()==null)return;
            try(InputStream in=getContentResolver().openInputStream(data.getData())) {
                String type=getContentResolver().getType(data.getData());
                crm.saveLogo(in,type);
                businessScreen();
                notice("Logo saved","New estimates and invoices will include this logo.");
            }catch(Exception e){error(e);}
            return;
        }
        if(requestCode==ATTACHMENT_REQUEST||requestCode==BULK_PHOTO_REQUEST){
            if(resultCode==RESULT_OK && data!=null)saveSelectedAttachments(
                data,requestCode==BULK_PHOTO_REQUEST);
            else pendingAttachmentJobId=null;
            return;
        }
        if(requestCode==ATTACHMENT_EXPORT_REQUEST){
            if(resultCode!=RESULT_OK||data==null||data.getData()==null)return;
            try {
                CrmWorkspace.Attachment selected=pendingAttachmentExport;
                if(selected==null && pendingAttachmentExportId!=null &&
                    pendingAttachmentExportJob!=null){
                    for(CrmWorkspace.Attachment item:crm.attachments(
                        jobById(pendingAttachmentExportJob)))
                        if(item.id.equals(pendingAttachmentExportId))selected=item;
                }
                if(selected==null||pendingAttachmentExportJob==null)
                    throw new IOException("Attachment export expired");
                try(InputStream in=new FileInputStream(crm.fileFor(
                        jobById(pendingAttachmentExportJob),selected));
                    OutputStream out=getContentResolver().openOutputStream(data.getData(),"wt")) {
                    if(out==null)throw new IOException("Cannot open export destination");
                    byte[] bytes=new byte[8192];int got;
                    while((got=in.read(bytes))!=-1)out.write(bytes,0,got);
                    out.flush();
                }
                notice("File copied","Saved attachment to selected location.");
            }catch(Exception e){error(e);}
            finally {
                pendingAttachmentExport=null;
                pendingAttachmentExportId=null;
                pendingAttachmentExportJob=null;
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
                new ContactDirectory(store).add(cursor.getString(0),
                    cursor.getString(1),"");
                contactsScreen();
                notice("Contact saved","This person is in Contacts, not Customers.");
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
                store.addPhoto(work, input,getContentResolver().getType(data.getData()));
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
        if("contact".equals(currentScreen)){contactsScreen();return;}
        if("job_template".equals(currentScreen)||"catalog".equals(currentScreen)){
            businessScreen();return;
        }
        if(currentJobId!=null){
            if(currentCustomerId!=null)customer(currentCustomerId);
            else jobsScreen();
            return;
        }
        if(currentCustomerId!=null){customersScreen();return;}
        if("contacts".equals(currentScreen)||"customers".equals(currentScreen)||
            "jobs".equals(currentScreen)||"calendar".equals(currentScreen)||
            "schedule".equals(currentScreen)||"business".equals(currentScreen)){
            home();return;
        }
        super.onBackPressed();
    }


}
