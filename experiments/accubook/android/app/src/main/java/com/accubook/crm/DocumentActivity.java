package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.os.Bundle;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.content.Context;
import android.text.Html;
import android.view.View;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONArray;
import org.json.JSONTokener;

import java.io.IOException;
import java.util.List;

/**
 * Offline HTML-on-paper invoice/quote editor. The editable text is part of the
 * actual print document. Line items and totals are merged from canonical records.
 */
public final class DocumentActivity extends Activity {
    private static final int DARK=Color.rgb(10,15,29);
    private static final int LIGHT=Color.rgb(240,244,255);
    private WorkspaceStore store;
    private CrmWorkspace crm;
    private WorkspaceStore.Job job;
    private WorkspaceStore.Customer customer;
    private WebView preview;
    private boolean quote;

    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private void action(LinearLayout parent,String label,Runnable handler) {
        Button b=new Button(this);
        b.setAllCaps(false);
        b.setText(label);
        b.setTextSize(15);
        b.setTextColor(Color.WHITE);
        b.setMinHeight(dp(48));
        b.setBackgroundTintList(ColorStateList.valueOf(Color.rgb(26,104,184)));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);
        lp.setMargins(dp(5),dp(3),dp(5),dp(3));
        parent.addView(b,lp);
        b.setOnClickListener(v->handler.run());
    }
    private void error(Exception e) {
        new AlertDialog.Builder(this).setTitle("Document action failed")
            .setMessage(e.getMessage()==null?"Unable to complete action":e.getMessage())
            .setPositiveButton("OK",(d,w)->{}).show();
    }
    private static final int UNLOCK_REQUEST=854;
    private boolean unlocked=false;
    private long lastHiddenAt=0;
    private boolean unlocking=false;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        if((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE)!=0)
            AnnotationUi.install(this,()->unlocked?"document_editor":"locked");
        if(UnlockActivity.isEnabled(this)){
            getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
            showLock();
            return;
        }
        unlocked=true;
        initializeDocument();
    }

    private void showLock() {
        TextView view=new TextView(this);
        view.setText("Document locked. Confirm fingerprint or device PIN.");
        view.setTextSize(20);
        view.setTextColor(LIGHT);
        view.setBackgroundColor(DARK);
        view.setPadding(dp(24),dp(50),dp(24),dp(30));
        setContentView(view);
        if(!unlocking){
            unlocking=true;
            startActivityForResult(new Intent(this,UnlockActivity.class),UNLOCK_REQUEST);
        }
    }
    @Override protected void onStart(){
        super.onStart();
        if(unlocked && UnlockActivity.isEnabled(this) && !unlocking && lastHiddenAt>0 &&
            android.os.SystemClock.elapsedRealtime()-lastHiddenAt>30000) {
            unlocked=false;
            showLock();
        }
    }
    @Override protected void onStop(){
        if(UnlockActivity.isEnabled(this))lastHiddenAt=android.os.SystemClock.elapsedRealtime();
        super.onStop();
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==UNLOCK_REQUEST){
            unlocking=false;
            if(result==RESULT_OK){
                unlocked=true;
                if(store==null)initializeDocument();
                else try{build();}catch(Exception error){error(error);}
            }else showLockedUntilRetry();
        }
    }
    private void showLockedUntilRetry(){
        android.widget.Button button=new android.widget.Button(this);
        button.setText("Unlock document");
        button.setOnClickListener(v->showLock());
        setContentView(button);
    }

    private void initializeDocument() {
        quote=getIntent().getBooleanExtra("estimate",false);
        String jobId=getIntent().getStringExtra("job");
        try {
            store=new WorkspaceStore(this);
            crm=new CrmWorkspace(store);
            if(jobId==null)throw new IOException("No job selected");
            for(WorkspaceStore.Job item:store.jobs())
                if(item.id.equals(jobId))job=item;
            if(job==null)throw new IOException("Job not found");
            for(WorkspaceStore.Customer client:store.customers())
                if(client.id.equals(job.customerId))customer=client;
            if(customer==null)throw new IOException("Customer not found");
            build();
        } catch (Exception e) {
            TextView message=new TextView(this);
            message.setText("Cannot open document: "+e.getMessage());
            message.setTextSize(18);
            setContentView(message);
        }
    }
    private void build() throws IOException {
        getWindow().setStatusBarColor(DARK);
        LinearLayout main=new LinearLayout(this);
        main.setOrientation(LinearLayout.VERTICAL);
        main.setBackgroundColor(DARK);
        setContentView(main);

        TextView title=new TextView(this);
        title.setText(quote?"Estimate · live document editor":
            "Invoice · live document editor");
        title.setTextColor(LIGHT);
        title.setTextSize(21);
        title.setPadding(dp(15),dp(12),dp(12),dp(7));
        if(android.os.Build.VERSION.SDK_INT>=28)title.setAccessibilityHeading(true);
        main.addView(title);
        TextView hint=new TextView(this);
        hint.setText("Tap outlined Message or Closing text inside the page to edit it. "
            +"The invoice rows merge from the job. Save changes before leaving.");
        hint.setTextColor(LIGHT);
        hint.setTextSize(13);
        hint.setPadding(dp(15),dp(2),dp(12),dp(8));
        main.addView(hint);

        ScrollView controls=new ScrollView(this);
        LinearLayout actions=new LinearLayout(this);
        actions.setOrientation(LinearLayout.VERTICAL);
        controls.addView(actions);
        LinearLayout.LayoutParams controlHeight=new LinearLayout.LayoutParams(-1,dp(265));
        main.addView(controls,controlHeight);

        LinearLayout format=new LinearLayout(this);
        format.setOrientation(LinearLayout.HORIZONTAL);
        actions.addView(format);
        formatButton(format,"Bold","bold");
        formatButton(format,"Italic","italic");
        formatButton(format,"Underline","underline");

        action(actions,"Save edited document sections",()->saveRich(false,false));
        action(actions,"Save current layout as default template",()->saveRich(false,true));
        action(actions,"Print / Save as PDF",()->saveRich(true,false));
        action(actions,"Refresh merged customer and line items",()->{
            try{render();}
            catch(Exception error){error(error);}
        });
        if(quote) {
            action(actions,"Share estimate text using installed app",this::shareQuote);
            action(actions,"Mark estimate sent / unsent",this::quoteStatus);
        }
        preview=new WebView(this);
        preview.setBackgroundColor(Color.WHITE);
        preview.getSettings().setJavaScriptEnabled(true);
        preview.getSettings().setAllowFileAccess(false);
        preview.getSettings().setAllowContentAccess(false);
        preview.getSettings().setJavaScriptCanOpenWindowsAutomatically(false);
        preview.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,String url){return true;}
        });
        main.addView(preview,new LinearLayout.LayoutParams(-1,0,1));
        render();
    }
    private void formatButton(LinearLayout row,String label,String command) {
        Button b=new Button(this);
        b.setAllCaps(false);
        b.setText(label);
        b.setTextSize(12);
        b.setTextColor(LIGHT);
        b.setBackgroundTintList(ColorStateList.valueOf(Color.rgb(34,55,80)));
        row.addView(b,new LinearLayout.LayoutParams(0,dp(48),1));
        b.setOnClickListener(v->preview.evaluateJavascript(
            "document.execCommand('"+command+"',false,null)",null));
    }
    private void render() throws IOException {
        // Reload replaces any unsaved visual edits; this is an explicit action.
        if(preview==null)return;
        job=findJob();

        CrmWorkspace.Branding brand=crm.branding();
        byte[] logo=crm.logo();
        // New Jules Gutter Cleaning workspaces show the user-provided leaf, without
        // overwriting custom logos or setting a permanent preference.
        if(logo.length==0 && brand.logoMime.isEmpty() &&
                "Jules Gutter Cleaning".equals(brand.business)){
            try(java.io.InputStream in=getResources().openRawResource(
                    R.drawable.accubook_business_leaf);
                java.io.ByteArrayOutputStream bytes=new java.io.ByteArrayOutputStream()){
                byte[] block=new byte[4096];int count;
                while((count=in.read(block))!=-1)bytes.write(block,0,count);
                logo=bytes.toByteArray();
                brand=brand.withLogoMime("image/png");
            }
        }
        String html=InvoiceHtml.renderDocument(customer,job,store.items(job),brand,
            crm.memo(job),logo,quote,true);
        preview.loadDataWithBaseURL(null,html,"text/html","UTF-8",null);
    }
    private WorkspaceStore.Job findJob() throws IOException {
        for(WorkspaceStore.Job j:store.jobs())
            if(j.id.equals(job.id))return j;
        throw new IOException("Job deleted while editing");
    }
    private void saveRich(boolean print,boolean asDefault) {
        // View reads only two editable areas; never accept script or arbitrary HTML.
        String code="(function(){return JSON.stringify(["
            +"document.getElementById('greeting').innerHTML,"
            +"document.getElementById('closing').innerHTML]);})()";
        preview.evaluateJavascript(code,result->{
            try{
                Object decoded=new JSONTokener(result).nextValue();
                if(!(decoded instanceof String))throw new IOException("Cannot read editor content");
                JSONArray values=new JSONArray((String)decoded);
                String greeting=InvoiceHtml.safeRichFragment(values.getString(0));
                String closing=InvoiceHtml.safeRichFragment(values.getString(1));
                crm.saveMemo(job,greeting,closing);
                if(asDefault)crm.saveDefaultMemo(greeting,closing);
                Toast.makeText(this,asDefault?"Default template saved for new jobs":
                    "Document edits saved locally",Toast.LENGTH_SHORT).show();
                if(print) printPdf();
            }catch(Exception e){error(e);}
        });
    }
    private void printPdf() {
        try {
            PrintManager printer=(PrintManager)getSystemService(Context.PRINT_SERVICE);
            if(printer==null)throw new IOException("Android printing is unavailable");
            printer.print(DocumentNumbers.reference(job.id,job.date,quote),
                preview.createPrintDocumentAdapter(
                    DocumentNumbers.reference(job.id,job.date,quote)),
                new PrintAttributes.Builder()
                    .setMediaSize(PrintAttributes.MediaSize.NA_LETTER)
                    .setColorMode(PrintAttributes.COLOR_MODE_COLOR)
                    .build());
            Toast.makeText(this,"Choose Save as PDF in Android print destination",
                Toast.LENGTH_LONG).show();
        }catch(Exception e){error(e);}
    }
    private void shareQuote() {
        try {
            // Plain message handoff; external apps handle actual delivery.
            String text=Html.fromHtml(InvoiceHtml.renderDocument(customer,findJob(),
                store.items(job),crm.branding(),crm.memo(job),crm.logo(),true,false),
                Html.FROM_HTML_MODE_COMPACT).toString();
            Intent send=new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_SUBJECT,"Estimate - "+job.title);
            send.putExtra(Intent.EXTRA_TEXT,text);
            startActivity(Intent.createChooser(send,"Share estimate with"));
            Toast.makeText(this,"After sending, mark Estimate sent separately",
                Toast.LENGTH_LONG).show();
        }catch(Exception e){error(e);}
    }
    private void quoteStatus() {
        try {
            CrmWorkspace.Quote state=crm.quote(job);
            new AlertDialog.Builder(this).setTitle("Estimate sent status")
                .setMessage(state.sent?"Marked sent on "+state.sentDate+
                    ". This is a manual delivery flag, not proof of delivery.":
                    "Mark sent only after your message has actually been sent.")
                .setNegativeButton("Cancel",(d,w)->{})
                .setPositiveButton(state.sent?"Mark unsent":"Mark sent",(d,w)->{
                    try {
                        crm.setQuoteSent(job,!state.sent,"Manually confirmed by user");
                        Toast.makeText(this,!state.sent?"Estimate marked sent":"Estimate marked unsent",
                            Toast.LENGTH_SHORT).show();
                    }catch(Exception e){error(e);}
                }).show();
        }catch(Exception e){error(e);}
    }
}
