package com.accubook.crm;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.KeyguardManager;
import android.app.admin.DevicePolicyManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.hardware.biometrics.BiometricPrompt;
import android.os.Build;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.concurrent.Executor;

/**
 * Optional OS-mediated lock using enrolled fingerprint or screen-lock PIN.
 * This is access control only: it does NOT encrypt files on disk.
 * Never stores a custom PIN, biometric material or passcode.
 */
public final class UnlockActivity extends Activity {
    private static final int CREDENTIAL=852;
    public static final String PREFERENCES="accubook.security";
    public static final String ENABLED="require_unlock";
    private boolean inProgress=false;
    private CancellationSignal cancellation;

    public static boolean isEnabled(Context context){
        return context.getSharedPreferences(PREFERENCES,MODE_PRIVATE).getBoolean(ENABLED,false);
    }
    public static void setEnabled(Context context,boolean value){
        context.getSharedPreferences(PREFERENCES,MODE_PRIVATE).edit()
            .putBoolean(ENABLED,value).apply();
    }
    public static boolean isSecure(Context context){
        KeyguardManager keyguard=(KeyguardManager)context.getSystemService(KEYGUARD_SERVICE);
        return keyguard!=null&&keyguard.isDeviceSecure();
    }

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        LinearLayout layout=new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.rgb(10,15,29));
        int pad=(int)(24*getResources().getDisplayMetrics().density);
        layout.setPadding(pad,pad,pad,pad);
        TextView heading=new TextView(this);
        heading.setText("Accubook is locked");
        heading.setTextSize(27);
        heading.setTextColor(Color.WHITE);
        layout.addView(heading);
        TextView explanation=new TextView(this);
        explanation.setText("Unlock with your enrolled fingerprint or Android device PIN, "
            +"pattern, or password. Nothing is sent to a server.");
        explanation.setTextSize(17);
        explanation.setTextColor(Color.LTGRAY);
        explanation.setPadding(0,pad,0,pad);
        layout.addView(explanation);
        Button unlock=new Button(this);
        unlock.setText("Unlock Accubook");
        unlock.setMinHeight((int)(54*getResources().getDisplayMetrics().density));
        layout.addView(unlock);
        unlock.setOnClickListener(v->authenticate());
        Button cancel=new Button(this);
        cancel.setText("Keep locked");
        layout.addView(cancel);
        cancel.setOnClickListener(v->{setResult(RESULT_CANCELED);finish();});
        setContentView(layout);
        if(saved==null)unlock.post(this::authenticate);
    }

    private void success() {
        inProgress=false;
        setResult(RESULT_OK);
        finish();
    }
    private void authenticate() {
        if(inProgress)return;
        if(!isSecure(this)){
            new AlertDialog.Builder(this).setTitle("Screen lock required")
                .setMessage("Set a secure Android screen lock first. Accubook will not "
                    +"bypass an unprotected device.")
                .setPositiveButton("OK",(d,w)->{}).show();
            return;
        }
        inProgress=true;
        if(Build.VERSION.SDK_INT>=30) {
            try{
                cancellation=new CancellationSignal();
                Executor executor=getMainExecutor();
                BiometricPrompt prompt=new BiometricPrompt.Builder(this)
                    .setTitle("Unlock Accubook")
                    .setSubtitle("Fingerprint or device PIN/pattern/password")
                    .setAllowedAuthenticators(
                        android.hardware.biometrics.BiometricManager.Authenticators.BIOMETRIC_STRONG |
                        android.hardware.biometrics.BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                    .build();
                prompt.authenticate(cancellation,executor,
                    new BiometricPrompt.AuthenticationCallback(){
                        @Override public void onAuthenticationSucceeded(
                            BiometricPrompt.AuthenticationResult result){success();}
                        @Override public void onAuthenticationError(int code,CharSequence message){
                            inProgress=false;
                            if(!isFinishing())new AlertDialog.Builder(UnlockActivity.this)
                                .setTitle("Not unlocked").setMessage(message)
                                .setPositiveButton("Try again",(d,w)->authenticate())
                                .setNegativeButton("Cancel",(d,w)->{}).show();
                        }
                    });
                return;
            }catch(Exception failure){
                inProgress=false; // Allow secure device-credential fallback.
            }
        }
        // Compatible fallback for API 26-29, using Android's credential prompt.
        try {
            KeyguardManager keyguard=(KeyguardManager)getSystemService(KEYGUARD_SERVICE);
            Intent challenge=keyguard.createConfirmDeviceCredentialIntent(
                "Unlock Accubook","Confirm your device's screen lock");
            if(challenge==null)throw new IllegalStateException("Device credential unavailable");
            startActivityForResult(challenge,CREDENTIAL);
        }catch(Exception error){
            inProgress=false;
            new AlertDialog.Builder(this).setTitle("Cannot unlock")
                .setMessage(error.getMessage()).setPositiveButton("OK",(d,w)->{}).show();
        }
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==CREDENTIAL){
            inProgress=false;
            if(result==RESULT_OK)success();
        }
    }
    @Override protected void onDestroy(){
        if(cancellation!=null && !inProgress)cancellation.cancel();
        super.onDestroy();
    }
}
