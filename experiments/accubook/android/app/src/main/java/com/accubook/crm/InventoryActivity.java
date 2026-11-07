package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.graphics.Color;
import android.content.res.ColorStateList;
import android.text.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

/** Deliberately small field/office UI, no role walls or mandatory scrolling table. */
public final class InventoryActivity extends Activity {
    private static final int BG=0xFF0D1626, FG=0xFFF6FAFF, MUTED=0xFFC9D8E8;
    private static final int ACTION_COLOR=0xFF177EC6;
    private WorkspaceStore workspace;
    private InventoryStore inventory;
    private LinearLayout root;
    private String preferredJob;
    private int dp(int px){return (int)(px*getResources().getDisplayMetrics().density+0.5f);}
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);
        getWindow().setStatusBarColor(BG);getWindow().setNavigationBarColor(BG);
        preferredJob=getIntent().getStringExtra("jobId");
        try{
            workspace=new WorkspaceStore(this);
            inventory=new InventoryStore(workspace);
            render();
        }catch(Exception error){showError(error);}
    }
    private TextView label(LinearLayout holder,String text,int size,int color){
        TextView view=new TextView(this);
        view.setText(text);view.setTextColor(color);view.setTextSize(size);
        view.setPadding(dp(3),dp(7),dp(3),dp(8));
        holder.addView(view,new LinearLayout.LayoutParams(-1,-2));
        return view;
    }
    private Button button(LinearLayout holder,String title,Runnable work){
        Button view=new Button(this);
        view.setText(title);view.setAllCaps(false);
        view.setTextColor(FG);view.setTextSize(16);
        view.setMinHeight(dp(55));
        view.setBackgroundTintList(ColorStateList.valueOf(ACTION_COLOR));
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2);
        params.setMargins(0,dp(3),0,dp(3));
        holder.addView(view,params);
        view.setOnClickListener(v->work.run());
        return view;
    }
    private EditText input(LinearLayout area,String title,String hint){
        label(area,title,17,FG);
        EditText field=new EditText(this);
        field.setTextColor(FG);field.setHintTextColor(MUTED);
        field.setHint(hint);field.setContentDescription(title);
        field.setSingleLine(true);
        field.setMinHeight(dp(56));field.setTextSize(17);
        area.addView(field,new LinearLayout.LayoutParams(-1,-2));
        return field;
    }
    private LinearLayout form(){
        LinearLayout content=new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(19),dp(12),dp(19),dp(12));
        return content;
    }
    private void showError(Exception error){
        new AlertDialog.Builder(this).setTitle("Inventory not changed")
            .setMessage(error.getMessage()==null?"Check your item and quantity":error.getMessage())
            .setPositiveButton("OK",(d,w)->{}).show();
    }
    private void notice(String title,String message){
        new AlertDialog.Builder(this).setTitle(title).setMessage(message)
            .setPositiveButton("OK",(d,w)->{}).show();
    }
    private void render()throws Exception {
        ScrollView scroll=new ScrollView(this);
        scroll.setBackgroundColor(BG);
        root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18),dp(15),dp(18),dp(28));
        scroll.addView(root);setContentView(scroll);
        label(root,"Inventory",28,FG);
        label(root,"Company stock · Job sites · Tools",17,MUTED);
        label(root,"Add an item, receive it, move it to a job, use it, or return it. "
            +"Every move is recorded offline. No supplier connection.",15,MUTED);
        button(root,"＋ New material or tool",this::newItem);
        StockLedger.State state=inventory.state();
        List<WorkspaceStore.Job> jobs=workspace.jobs();
        if(state.items.isEmpty())label(root,"No inventory yet. Add your first material or tool.",17,FG);
        for(StockLedger.Item item:state.items){
            LinearLayout card=new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(13),dp(9),dp(13),dp(10));
            card.setBackgroundColor(0xFF1E3249);
            LinearLayout.LayoutParams box=new LinearLayout.LayoutParams(-1,-2);
            box.setMargins(0,dp(10),0,dp(4));
            root.addView(card,box);
            label(card,item.name+"  ·  "+(item.kind.equals(StockLedger.TOOL)?"Tool":"Material"),20,FG);
            label(card,"Company: "+state.balance(item.id,StockLedger.COMPANY).toPlainString()
                +" "+item.unit,17,FG);
            for(WorkspaceStore.Job job:jobs){
                BigDecimal count=state.balance(item.id,job.id);
                if(count.signum()>0)
                    label(card,job.title+" (job site): "+count.toPlainString()+" "+item.unit,
                        15,MUTED);
            }
            button(card,"Rename item",()->rename(item));
            button(card,"Receive stock",()->quantityDialog(item,StockLedger.RECEIVE,
                StockLedger.EXTERNAL,StockLedger.COMPANY));
            button(card,"Send to job",()->selectJob(item,StockLedger.TRANSFER,false));
            button(card,"Return from job",()->selectJob(item,StockLedger.TRANSFER,true));
            if(item.kind.equals(StockLedger.MATERIAL))
                button(card,"Mark used on job",()->selectJob(item,StockLedger.USE,false));
            button(card,"Correct company count",()->chooseCorrection(item));
        }
        label(root,"Stock is a movement history, not a pricebook or accounting ledger. "
            +"A rejected move cannot leave negative stock. Export a workspace backup "
            +"before making large changes.",14,MUTED);
        button(root,"Back to Accubook",this::finish);
    }
    private void rename(StockLedger.Item item){
        LinearLayout panel=form();
        EditText name=input(panel,"Item name","Name");
        name.setText(item.name);
        new AlertDialog.Builder(this).setTitle("Rename material or tool")
            .setView(panel).setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Save name",(d,w)->{
                try{inventory.renameItem(item.id,name.getText().toString());render();}
                catch(Exception error){showError(error);}
            }).show();
    }
    private void newItem(){
        LinearLayout panel=form();
        EditText name=input(panel,"Item name","e.g. Shingle bundles / ladder #3");
        EditText unit=input(panel,"Unit","each, box, bundle, gallon");
        new AlertDialog.Builder(this).setTitle("What kind of item?")
            .setItems(new String[]{"Material","Tool / equipment"},(d,choice)->{
                new AlertDialog.Builder(this).setTitle("New item").setView(panel)
                    .setNegativeButton("Cancel",(d1,w)->{})
                    .setPositiveButton("Add item",(d1,w)->{
                        try{
                            inventory.addItem(name.getText().toString(),
                                choice==0?StockLedger.MATERIAL:StockLedger.TOOL,
                                unit.getText().toString());
                            render();
                        }catch(Exception error){showError(error);}
                    }).show();
            }).setNegativeButton("Cancel",(d,w)->{}).show();
    }
    private void quantityDialog(StockLedger.Item item,String action,String from,String to){
        LinearLayout panel=form();
        EditText qty=input(panel,"How many "+item.unit+"?","1");
        qty.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);
        EditText note=input(panel,"Note / reason (optional for normal moves)",
            "e.g. Delivered at site");
        if(action.startsWith("ADJUST"))
            note.setHint("Reason required, e.g. physical count correction");
        new AlertDialog.Builder(this).setTitle(item.name+" · "+action.replace('_',' '))
            .setView(panel).setNegativeButton("Cancel",(d,w)->{})
            .setPositiveButton("Record move",(d,w)->{
                try{
                    inventory.move(item.id,action,from,to,qty.getText().toString(),
                        note.getText().toString());
                    render();
                }catch(Exception error){showError(error);}
            }).show();
    }
    private void selectJob(StockLedger.Item item,String action,boolean returnToCompany){
        try{
            StockLedger.State state=inventory.state();
            List<WorkspaceStore.Job> jobs=workspace.jobs(),eligible=new ArrayList<>();
            for(WorkspaceStore.Job job:jobs){
                if(returnToCompany||action.equals(StockLedger.USE)){
                    if(state.balance(item.id,job.id).signum()>0)eligible.add(job);
                }else eligible.add(job);
            }
            if(eligible.isEmpty()){
                notice("No available jobs","Create a job first, or receive stock before returning/using.");
                return;
            }
            String[] choices=new String[eligible.size()];
            int selected=0;
            for(int i=0;i<choices.length;i++){
                WorkspaceStore.Job job=eligible.get(i);
                choices[i]=job.title+" · "+job.date;
                if(job.id.equals(preferredJob))selected=i;
            }
            final int start=selected;
            new AlertDialog.Builder(this).setTitle("Choose job site")
                .setSingleChoiceItems(choices,selected,(dialog,index)->{
                    dialog.dismiss();
                    WorkspaceStore.Job job=eligible.get(index);
                    String from=returnToCompany||StockLedger.USE.equals(action)?
                        job.id:StockLedger.COMPANY;
                    String to=StockLedger.USE.equals(action)?StockLedger.CONSUMED:
                        returnToCompany?StockLedger.COMPANY:job.id;
                    quantityDialog(item,action,from,to);
                }).setNegativeButton("Cancel",(d,w)->{}).show();
        }catch(Exception error){showError(error);}
    }
    private void chooseCorrection(StockLedger.Item item){
        new AlertDialog.Builder(this).setTitle("Correct company count")
            .setMessage("Corrections stay in the movement history with a reason.")
            .setItems(new String[]{"Add found stock","Remove lost or damaged stock"},
                (d,index)->quantityDialog(item,index==0?StockLedger.ADJUST_IN:
                    StockLedger.ADJUST_OUT,index==0?StockLedger.EXTERNAL:
                    StockLedger.COMPANY,index==0?StockLedger.COMPANY:StockLedger.EXTERNAL))
            .setNegativeButton("Cancel",(d,w)->{}).show();
    }
}
