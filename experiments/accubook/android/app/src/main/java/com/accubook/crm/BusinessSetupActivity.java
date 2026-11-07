package com.accubook.crm;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.content.res.ColorStateList;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.TextView;
import android.app.AlertDialog;

/**
 * One-screen, offline setup. This Activity does not own jobs or customer data.
 * Existing workspaces never run setup destructively; the user can reopen it.
 */
public final class BusinessSetupActivity extends Activity {
    private static final int BG=0xFF0D1626, LIGHT=0xFFF6FAFF, MUTED=0xFFC9D8E8;
    private static final int ACCENT=0xFF177EC6;
    private int dp(int n){return (int)(getResources().getDisplayMetrics().density*n+0.5f);}
    private TextView label(LinearLayout host,String text,int size){
        TextView view=new TextView(this);
        view.setText(text);
        view.setTextColor(LIGHT);
        view.setTextSize(size);
        view.setPadding(0,dp(6),0,dp(8));
        host.addView(view,new LinearLayout.LayoutParams(-1,-2));
        return view;
    }
    private CheckBox check(LinearLayout host,String name,boolean initial){
        CheckBox view=new CheckBox(this);
        view.setText(name);
        view.setTextColor(LIGHT);
        view.setTextSize(17);
        view.setMinHeight(dp(56));
        view.setChecked(initial);
        host.addView(view,new LinearLayout.LayoutParams(-1,-2));
        return view;
    }
    private EditText input(LinearLayout host,String name,String value){
        EditText view=new EditText(this);
        view.setHint(name);
        view.setContentDescription(name);
        view.setTextColor(LIGHT);
        view.setHintTextColor(MUTED);
        view.setSingleLine(true);
        view.setTextSize(17);
        view.setText(value);
        view.setMinHeight(dp(56));
        host.addView(view,new LinearLayout.LayoutParams(-1,-2));
        return view;
    }
    private Button action(LinearLayout host,String name,Runnable callback){
        Button view=new Button(this);
        view.setText(name);
        view.setAllCaps(false);
        view.setTextSize(17);
        view.setMinHeight(dp(56));
        view.setTextColor(LIGHT);
        view.setBackgroundTintList(ColorStateList.valueOf(ACCENT));
        host.addView(view,new LinearLayout.LayoutParams(-1,-2));
        view.setOnClickListener(v->callback.run());
        return view;
    }
    @Override protected void onCreate(Bundle state){
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        try{render();}
        catch(Exception failure){
            new AlertDialog.Builder(this).setTitle("Setup unavailable")
                .setMessage("Your existing records were not changed. "+failure.getMessage())
                .setPositiveButton("Return",(d,w)->finish()).show();
        }
    }
    private BusinessSetupProfile initial() throws Exception {
        BusinessSetupProfile saved=BusinessSetupStore.load(this);
        if(saved!=null)return saved;
        boolean crews=FeatureSettings.enabled(this,FeatureSettings.CREW);
        return new BusinessSetupProfile(BusinessSetupProfile.NOT_STARTED,
            crews?BusinessSetupProfile.TEAM:BusinessSetupProfile.SOLO,"","",false,false,
            crews,FeatureSettings.enabled(this,FeatureSettings.CATALOG),
            FeatureSettings.enabled(this,FeatureSettings.WORKER_TIME),
            FeatureSettings.enabled(this,FeatureSettings.GPS),
            FeatureSettings.enabled(this,FeatureSettings.ADVANCED_CALENDAR),
            FeatureSettings.enabled(this,FeatureSettings.RECURRING));
    }
    private void render() throws Exception {
        BusinessSetupProfile previous=initial();
        ScrollView scroll=new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20),dp(16),dp(20),dp(28));
        scroll.addView(root);
        setContentView(scroll);

        label(root,"Make Accubook yours",27);
        label(root,"A few taps. Everything works offline. Change any answer later in Business.",16);
        label(root,"1 · How do you work?",20);
        RadioGroup team=new RadioGroup(this);
        team.setOrientation(RadioGroup.VERTICAL);
        RadioButton solo=new RadioButton(this);
        solo.setId(View.generateViewId());
        solo.setText("Just me · simple setup");
        solo.setTextColor(LIGHT);
        solo.setTextSize(17);
        solo.setMinHeight(dp(52));
        team.addView(solo);
        RadioButton crew=new RadioButton(this);
        crew.setId(View.generateViewId());
        crew.setText("I assign work to a crew");
        crew.setTextColor(LIGHT);
        crew.setTextSize(17);
        crew.setMinHeight(dp(52));
        team.addView(crew);
        root.addView(team);
        team.check(previous.crew?crew.getId():solo.getId());
        label(root,"2 · What kind of work?",20);
        EditText trade=input(root,"Primary trade (optional)",previous.trade);
        label(root,"Examples: gutters, roofing, fencing, tree service, auto repair.",14);
        label(root,"3 · What do you want to see?",20);
        CheckBox prices=check(root,"Services and materials pricebook",previous.catalog);
        CheckBox recurring=check(root,"Repeat-service reminders",previous.recurring);
        CheckBox inventory=check(root,"Materials, job-site stock and tools",previous.inventory);
        CheckBox time=check(root,"Record worker time (optional)",previous.workerTime);
        CheckBox gps=check(root,"Private GPS route capture (off by default)",previous.gps);
        label(root,"GPS never starts just because you enable its menu. "
            +"Advanced calendar sync stays unchanged and optional.",14);
        label(root,"4 · What gets delivered to jobs?",20);
        CheckBox materials=check(root,"I use material deliveries",previous.materialDeliveries);
        CheckBox dumpsters=check(root,"I use dumpsters",previous.dumpsters);
        EditText vendors=input(root,"Suppliers / vendors (optional)",previous.vendors);
        label(root,"Delivery and dumpster choices are saved as preferences. "
            +"Edit each job's checklist in Jobs; supplier ordering is not connected.",14);
        action(root,"Save setup · open Accubook",()->{
            try{
                BusinessSetupProfile selected=new BusinessSetupProfile(
                    BusinessSetupProfile.COMPLETE,
                    team.getCheckedRadioButtonId()==crew.getId()?
                        BusinessSetupProfile.TEAM:BusinessSetupProfile.SOLO,
                    trade.getText().toString(),vendors.getText().toString(),
                    materials.isChecked(),dumpsters.isChecked(),
                    team.getCheckedRadioButtonId()==crew.getId(),
                    prices.isChecked(),time.isChecked(),gps.isChecked(),
                    previous.advancedCalendar,recurring.isChecked(),inventory.isChecked());
                BusinessSetupStore.save(this,selected);
                setResult(RESULT_OK);
                finish();
            }catch(Exception error){showError(error);}
        });
        action(root,"Skip setup · use basic defaults",()->{
            try{
                BusinessSetupStore.save(this,new BusinessSetupProfile(
                    BusinessSetupProfile.SKIPPED,previous.team,
                    previous.trade,previous.vendors,previous.materialDeliveries,
                    previous.dumpsters,previous.crew,previous.catalog,
                    previous.workerTime,previous.gps,previous.advancedCalendar,
                    previous.recurring,previous.inventory));
                setResult(RESULT_OK);
                finish();
            }catch(Exception error){showError(error);}
        });
        label(root,"No account, subscription, camera, location permission or AI needed.",14);
    }
    private void showError(Exception error){
        new AlertDialog.Builder(this).setTitle("Setup not saved")
            .setMessage(error.getMessage()==null?"Could not save your choices":error.getMessage())
            .setPositiveButton("OK",(d,w)->{}).show();
    }
}
