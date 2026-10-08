package com.parallax.entrainment
import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.widget.*
import kotlin.math.roundToInt

class SettingsActivity:Activity(){
    private val bands=arrayOf("4.0 Hz - Delta / Deep Theta","6.0 Hz - Theta / Meditative","7.83 Hz - Schumann Resonance","10.0 Hz - Alpha / Relaxed Focus","15.0 Hz - Beta / Alert Cognition","40.0 Hz - Gamma / High Sync")
    private val p by lazy{getSharedPreferences(OverlayService.PREFS,MODE_PRIVATE)}
    private lateinit var hz:Spinner;private lateinit var mode:RadioGroup;private lateinit var volume:SeekBar;private lateinit var fullOpacity:SeekBar;private lateinit var borderWidth:SeekBar;private lateinit var borderOpacity:SeekBar;private lateinit var timedMinutes:EditText;private lateinit var sunset:Switch;private lateinit var timed:Switch
    override fun onCreate(b:Bundle?){super.onCreate(b)
        val root=ScrollView(this).apply{addView(LinearLayout(this@SettingsActivity).apply{orientation=LinearLayout.VERTICAL;setPadding(32,40,32,32);build(this)})}
        setContentView(root);checkOverlayPermission()
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),2001)
    }
    private fun build(root:LinearLayout){
        root.addView(TextView(this).apply{text="PARALLAX DISTORTION";textSize=26f;gravity=Gravity.CENTER})
        root.addView(TextView(this).apply{text="Neural Entrainment Engine";textSize=14f;gravity=Gravity.CENTER;setPadding(0,8,0,24)})
        root.addView(label("Hemi-Sync Target"));hz=Spinner(this).apply{adapter=ArrayAdapter(this@SettingsActivity,android.R.layout.simple_spinner_dropdown_item,bands);setSelection(p.getFloat(OverlayService.KEY_HZ,4f).let{x->bands.indexOfFirst{it.startsWith(x.toString())}.coerceAtLeast(0)})};root.addView(hz)
        root.addView(label("Display Mode"));mode=RadioGroup(this).apply{orientation=RadioGroup.VERTICAL;addView(RadioButton(this@SettingsActivity).apply{id=100;text="Border Overlay";isChecked=!p.getBoolean(OverlayService.KEY_FULL,false)});addView(RadioButton(this@SettingsActivity).apply{id=101;text="Full Screen Overlay";isChecked=p.getBoolean(OverlayService.KEY_FULL,false)})};root.addView(mode)
        val seed=EditText(this).apply{hint="Session seed";setText(p.getString(OverlayService.KEY_SEED,"PARALLAX_MOBILE"))};root.addView(seed)
        volume=slider(root,"Volume",0,100,(p.getFloat(OverlayService.KEY_VOLUME,.12f)*100).roundToInt())
        fullOpacity=slider(root,"Full Screen Opacity",10,100,(p.getFloat(OverlayService.KEY_FULL_OPACITY,1f)*100).roundToInt())
        borderWidth=slider(root,"Border Width",8,240,p.getFloat(OverlayService.KEY_BORDER_WIDTH,72f).roundToInt())
        borderOpacity=slider(root,"Border Opacity",0,100,(p.getFloat(OverlayService.KEY_BORDER_OPACITY,.75f)*100).roundToInt())
        root.addView(label("Automatic Scheduling"))
        sunset=Switch(this).apply{text="Start at sunset, stop at sunrise";isChecked=p.getBoolean(OverlayService.KEY_SUNSET_SUNRISE,false)};root.addView(sunset)
        timed=Switch(this).apply{text="Timed session";isChecked=p.getBoolean(OverlayService.KEY_TIMED,false)};root.addView(timed)
        timedMinutes=EditText(this).apply{hint="Timed duration (minutes)";inputType=InputType.TYPE_CLASS_NUMBER;setText(p.getInt(OverlayService.KEY_TIMED_MINUTES,5).toString())};root.addView(timedMinutes)
        val start=Button(this).apply{text="Start Session"};val stop=Button(this).apply{text="Stop Session"};root.addView(start);root.addView(stop)
        sunset.setOnCheckedChangeListener{_,v->p.edit().putBoolean(OverlayService.KEY_SUNSET_SUNRISE,v).apply();if(v){requestLocationAndSchedule()}else ScheduleReceiver.reschedule(this)}
        timed.setOnCheckedChangeListener{_,v->p.edit().putBoolean(OverlayService.KEY_TIMED,v).apply()}
        start.setOnClickListener{saveAndStart(seed)}
        stop.setOnClickListener{startService(Intent(this,OverlayService::class.java).apply{action=OverlayService.ACTION_STOP})}
    }
    private fun slider(root:LinearLayout,title:String,min:Int,max:Int,value:Int):SeekBar{
        val tv=label(title+"  "+value);root.addView(tv);val bar=SeekBar(this).apply{this.max=max-min;progress=(value-min).coerceIn(0,max-min)}
        bar.setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener{override fun onProgressChanged(s:SeekBar?,v:Int,f:Boolean){tv.text=title+"  "+(v+min)};override fun onStartTrackingTouch(s:SeekBar?){ };override fun onStopTrackingTouch(s:SeekBar?){}});root.addView(bar);return bar
    }
    private fun label(s:String)=TextView(this).apply{text=s;textSize=12f;setPadding(0,12,0,4)}
    private fun saveAndStart(seed:EditText){
        if(!Settings.canDrawOverlays(this)){checkOverlayPermission();return}
        val selected=bands[hz.selectedItemPosition].substringBefore(" ").toFloat();val minutes=timedMinutes.text.toString().toLongOrNull()?.coerceIn(1,720)?:5L;val full=mode.checkedRadioButtonId==101
        val seedText=seed.text.toString().ifBlank{"PARALLAX_MOBILE"};p.edit().putFloat(OverlayService.KEY_HZ,selected).putBoolean(OverlayService.KEY_FULL,full).putString(OverlayService.KEY_SEED,seedText).putFloat(OverlayService.KEY_VOLUME,volume.progress/100f).putFloat(OverlayService.KEY_FULL_OPACITY,fullOpacity.progress/100f).putFloat(OverlayService.KEY_BORDER_WIDTH,borderWidth.progress.toFloat()).putFloat(OverlayService.KEY_BORDER_OPACITY,borderOpacity.progress/100f).putInt(OverlayService.KEY_TIMED_MINUTES,minutes.toInt()).apply()
        val i=Intent(this,OverlayService::class.java).apply{putExtra(OverlayService.EXTRA_IS_FULL_OVERLAY,full);putExtra(OverlayService.EXTRA_TARGET_HZ,selected);putExtra(OverlayService.EXTRA_SEED,seedText);putExtra(OverlayService.EXTRA_VOLUME,volume.progress/100f);putExtra(OverlayService.EXTRA_FULL_OPACITY,fullOpacity.progress/100f);putExtra(OverlayService.EXTRA_BORDER_WIDTH,borderWidth.progress.toFloat());putExtra(OverlayService.EXTRA_BORDER_OPACITY,borderOpacity.progress/100f);if(timed.isChecked)putExtra(OverlayService.EXTRA_DURATION_MS,minutes*60000L)}
        if(Build.VERSION.SDK_INT>=26)startForegroundService(i)else startService(i)
    }
    private fun requestLocationAndSchedule(){
        if(Build.VERSION.SDK_INT>=23&&checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION),3001);return}
        ScheduleReceiver.reschedule(this)
    }
    override fun onRequestPermissionsResult(r:Int,p:Array<String>,g:IntArray){super.onRequestPermissionsResult(r,p,g);if(r==3001&&g.isNotEmpty()&&g[0]==PackageManager.PERMISSION_GRANTED)ScheduleReceiver.reschedule(this)}
    private fun checkOverlayPermission(){if(!Settings.canDrawOverlays(this))startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+packageName)))}
}