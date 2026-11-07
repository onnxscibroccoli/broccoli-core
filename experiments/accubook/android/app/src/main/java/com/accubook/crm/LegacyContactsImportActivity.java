package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.net.Uri;
import android.graphics.Color;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Owner-initiated CSV migration, with a read-only preview and separate commit.
 * Imports Contacts ONLY, never customers/jobs/invoices or external accounts.
 */
public final class LegacyContactsImportActivity extends Activity {
    private static final int PICK_CSV=902;
    private static final int BG=0xFF0D1626,LIGHT=0xFFF6FAFF,MUTED=0xFFC9D8E8;
    private LegacyContactsCsv selected;
    private LegacyContactsCsv.Preview pending;
    private LinearLayout content;
    private int dp(int value){return (int)(value*getResources().getDisplayMetrics().density+0.5f);}
    private TextView label(String message,int size){
        TextView text=new TextView(this);
        text.setText(message);text.setTextColor(LIGHT);text.setTextSize(size);
        text.setPadding(0,dp(8),0,dp(8));
        content.addView(text,new LinearLayout.LayoutParams(-1,-2));
        return text;
    }
    private Button button(String title,Runnable onClick){
        Button button=new Button(this);button.setText(title);button.setAllCaps(false);
        button.setTextSize(17);button.setTextColor(LIGHT);button.setMinHeight(dp(56));
        button.setBackgroundTintList(ColorStateList.valueOf(0xFF177EC6));
        content.addView(button,new LinearLayout.LayoutParams(-1,-2));
        button.setOnClickListener(v->onClick.run());return button;
    }
    @Override protected void onCreate(Bundle state){
        super.onCreate(state);getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        startScreen();
    }
    private void startScreen(){
        ScrollView scroll=new ScrollView(this);scroll.setBackgroundColor(BG);
        content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20),dp(16),dp(20),dp(30));
        scroll.addView(content);setContentView(scroll);
        label("Move contacts from another CRM",26);
        label("Choose a CSV export. Check the columns, preview names, then confirm. "
            +"No customer or job will be created.",17);
        button("Choose contact CSV file",this::selectFile);
        label("Private and offline · Up to 2 MB or 5,000 rows per import. "
            +"Existing contacts are not overwritten. Create a workspace backup first.",15);
        if(selected!=null)showColumns();
    }
    private void selectFile(){
        try{
            Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
            pick.addCategory(Intent.CATEGORY_OPENABLE);
            pick.setType("*/*");
            pick.putExtra(Intent.EXTRA_MIME_TYPES,
                new String[]{"text/csv","text/plain","text/comma-separated-values",
                    "application/vnd.ms-excel","application/octet-stream"});
            pick.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(pick,PICK_CSV);
        }catch(Exception error){problem(error);}
    }
    @Override protected void onActivityResult(int code,int result,Intent data){
        super.onActivityResult(code,result,data);
        if(code!=PICK_CSV||result!=RESULT_OK||data==null||data.getData()==null)return;
        Uri selectedFile=data.getData();
        pending=null;
        buttonDisabledWhileLoading();
        new Thread(()->{
            try{
                String input=readCsv(selectedFile);
                LegacyContactsCsv parsed=LegacyContactsCsv.parse(input);
                runOnUiThread(()->{
                    selected=parsed;
                    startScreen();
                });
            }catch(Exception error){runOnUiThread(()->{
                startScreen();
                problem(error);
            });}
        },"accubook-csv-import-read").start();
    }
    private void buttonDisabledWhileLoading(){
        content.removeAllViews();
        label("Reading local CSV…",19);
    }
    private String readCsv(Uri uri) throws IOException {
        try(InputStream input=getContentResolver().openInputStream(uri);
            ByteArrayOutputStream result=new ByteArrayOutputStream()){
            if(input==null)throw new IOException("No readable file returned");
            byte[] chunk=new byte[8192];int read;
            while((read=input.read(chunk))!=-1){
                if(result.size()+read>LegacyContactsCsv.MAX_BYTES)
                    throw new IOException("CSV exceeds 2 MB");
                result.write(chunk,0,read);
            }
            try{
                return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(result.toByteArray())).toString();
            }catch(java.nio.charset.CharacterCodingException error){
                throw new IOException("CSV is not UTF-8. Re-export as UTF-8.",error);
            }
        }
    }
    private Spinner spinner(String title,boolean optional,int guess){
        label(title,17);
        List<String> options=new ArrayList<>();
        if(optional)options.add("None · don't import this field");
        options.addAll(selected.headers());
        ArrayAdapter<String> adapter=new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_item,options);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        Spinner spinner=new Spinner(this);
        spinner.setContentDescription(title);
        spinner.setAdapter(adapter);spinner.setMinimumHeight(dp(55));
        content.addView(spinner,new LinearLayout.LayoutParams(-1,dp(55)));
        if(guess>=0)spinner.setSelection(guess+(optional?1:0));
        return spinner;
    }
    private void showColumns(){
        pending=null;
        label(selected.count()+" rows found · Check each column:",19);
        if(selected.guess("name")<0)
            label("Name not recognized, or multiple name columns found. "
                +"Choose the correct column before Preview.",15);
        Spinner names=spinner("Name · required",false,selected.guess("name"));
        Spinner phones=spinner("Phone · optional",true,selected.guess("phone"));
        Spinner emails=spinner("Email · optional",true,selected.guess("email"));
        button("Preview contacts before import",()->{
            try{
                pending=selected.preview(names.getSelectedItemPosition(),
                    phones.getSelectedItemPosition()-1,emails.getSelectedItemPosition()-1);
                showPreview(names,phones,emails);
            }catch(Exception error){problem(error);}
        });
    }
    private void showPreview(Spinner names,Spinner phones,Spinner emails){
        LegacyContactsCsv.Preview snapshot=pending;
        if(snapshot==null)return;
        label(snapshot.entries.size()+" named contacts ready · "+snapshot.skipped+
            " unnamed rows omitted · existing duplicates filtered on import.",17);
        for(int i=0;i<Math.min(4,snapshot.entries.size());i++){
            LegacyContactsCsv.Entry entry=snapshot.entries.get(i);
            label("• "+entry.name+(entry.phone.isEmpty()?"":" · "+entry.phone),15);
        }
        Button confirm=button("Import "+snapshot.entries.size()+" into Contacts",()->{
            // A preview is bound to the exact selected columns. Changes invalidate it.
            int name=names.getSelectedItemPosition();
            int phone=phones.getSelectedItemPosition()-1;
            int email=emails.getSelectedItemPosition()-1;
            try{
                if(!same(snapshot,selected.preview(name,phone,email))){
                    pending=null;notice("Mapping changed","Preview the new column mapping first.");
                    return;
                }
            }catch(Exception error){problem(error);return;}
            new AlertDialog.Builder(this).setTitle("Import contacts only?")
                .setMessage(snapshot.entries.size()+" contacts from "+
                    snapshot.sourceRows+" source rows. "+snapshot.skipped+
                    " unnamed rows will be skipped. Existing duplicate phone/email "
                    +"records will be skipped. Customers and jobs remain unchanged.")
                .setNegativeButton("Review",(d,w)->{})
                .setPositiveButton("Import",(d,w)->commit(snapshot))
                .show();
        });
        confirm.setContentDescription("Import previewed contacts into Contacts, not Customers");
    }
    private static boolean same(LegacyContactsCsv.Preview a,LegacyContactsCsv.Preview b){
        if(a.sourceRows!=b.sourceRows||a.skipped!=b.skipped||
            a.entries.size()!=b.entries.size())return false;
        for(int i=0;i<a.entries.size();i++){
            LegacyContactsCsv.Entry x=a.entries.get(i),y=b.entries.get(i);
            if(!x.source.equals(y.source)||!x.name.equals(y.name)||
                !x.phone.equals(y.phone)||!x.email.equals(y.email))return false;
        }
        return true;
    }
    private void commit(LegacyContactsCsv.Preview preview){
        content.removeAllViews();label("Saving Contacts…",20);
        new Thread(()->{
            try{
                WorkspaceStore store=new WorkspaceStore(this);
                List<ContactDirectory.ImportEntry> entries=new ArrayList<>();
                for(LegacyContactsCsv.Entry record:preview.entries)
                    entries.add(new ContactDirectory.ImportEntry(record.source,
                        record.name,record.phone,record.email));
                ContactDirectory.Result outcome=new ContactDirectory(store).importBatch(entries);
                runOnUiThread(()->new AlertDialog.Builder(this)
                    .setTitle("Contact import completed")
                    .setMessage(outcome.added+" added, "+outcome.skipped+
                        " duplicates skipped. No customer or job created.")
                    .setCancelable(false)
                    .setPositiveButton("Back to Contacts",(d,w)->{
                        setResult(RESULT_OK);finish();
                    }).show());
            }catch(Exception error){runOnUiThread(()->{
                startScreen();problem(error);
            });}
        },"accubook-csv-contact-commit").start();
    }
    private void problem(Exception error){notice("Import not completed",
        error.getMessage()==null?"File could not be read or saved":error.getMessage());}
    private void notice(String title,String message){
        new AlertDialog.Builder(this).setTitle(title).setMessage(message)
            .setPositiveButton("OK",(d,w)->{}).show();
    }
}
