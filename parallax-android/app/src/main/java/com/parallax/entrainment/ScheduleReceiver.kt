package com.parallax.entrainment
import android.Manifest
import android.app.*
import android.content.*
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.provider.Settings
import java.util.Calendar
import kotlin.math.*

class ScheduleReceiver:BroadcastReceiver(){
    override fun onReceive(c:Context,i:Intent?){
        val p=c.getSharedPreferences(OverlayService.PREFS,Context.MODE_PRIVATE)
        when(i?.action){ACTION_SUNSET->start(c);ACTION_SUNRISE->stop(c);Intent.ACTION_BOOT_COMPLETED,Intent.ACTION_MY_PACKAGE_REPLACED->if(p.getBoolean(OverlayService.KEY_SUNSET_SUNRISE,false))reschedule(c)}
    }
    private fun start(c:Context){if(!Settings.canDrawOverlays(c))return;val i=Intent(c,OverlayService::class.java);if(Build.VERSION.SDK_INT>=26)c.startForegroundService(i)else c.startService(i);reschedule(c)}
    private fun stop(c:Context){c.startService(Intent(c,OverlayService::class.java).apply{action=OverlayService.ACTION_STOP});reschedule(c)}
    companion object{
        const val ACTION_SUNSET="com.parallax.entrainment.SUNSET";const val ACTION_SUNRISE="com.parallax.entrainment.SUNRISE";private const val RS=7001;private const val RR=7002
        fun reschedule(c:Context){
            val p=c.getSharedPreferences(OverlayService.PREFS,Context.MODE_PRIVATE);val am=c.getSystemService(AlarmManager::class.java)
            am.cancel(pi(c,ACTION_SUNSET,RS));am.cancel(pi(c,ACTION_SUNRISE,RR));if(!p.getBoolean(OverlayService.KEY_SUNSET_SUNRISE,false))return
            val l=location(c)?:return;val now=System.currentTimeMillis();val day=SunTimes.forDate(l.latitude,l.longitude,Calendar.getInstance())
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,next(now,day.sunset),pi(c,ACTION_SUNSET,RS));am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,next(now,day.sunrise),pi(c,ACTION_SUNRISE,RR))
        }
        private fun pi(c:Context,a:String,r:Int)=PendingIntent.getBroadcast(c,r,Intent(c,ScheduleReceiver::class.java).setAction(a),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        private fun next(now:Long,t:Calendar)=if(t.timeInMillis>now)t.timeInMillis else t.timeInMillis+86400000L
        private fun location(c:Context):Location?{if(Build.VERSION.SDK_INT>=23&&c.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED)return null;val lm=c.getSystemService(LocationManager::class.java);return listOf(LocationManager.NETWORK_PROVIDER,LocationManager.GPS_PROVIDER).mapNotNull{runCatching{lm.getLastKnownLocation(it)}.getOrNull()}.maxByOrNull{it.time}}
    }
}
object SunTimes{
    data class Result(val sunrise:Calendar,val sunset:Calendar)
    fun forDate(lat:Double,lon:Double,base:Calendar):Result{
        fun calc(rise:Boolean):Calendar{
            val n=base.get(Calendar.DAY_OF_YEAR);val lh=lon/15.0;val t=n+((if(rise)6 else 18)-lh)/24.0;val m=.9856*t-3.289
            var l=m+1.916*sin(Math.toRadians(m))+.020*sin(Math.toRadians(2*m))+282.634;l=(l%360+360)%360
            var ra=Math.toDegrees(atan(.91764*tan(Math.toRadians(l))));ra=(ra%360+360)%360;ra+=(floor(l/90)*90-floor(ra/90)*90)/15
            val sd=.39782*sin(Math.toRadians(l));val cd=cos(asin(sd));val ch=(cos(Math.toRadians(90.833))-sin(Math.toRadians(lat))*sd)/(cos(Math.toRadians(lat))*cd)
            val h=if(rise)360-Math.toDegrees(acos(ch))else Math.toDegrees(acos(ch));val local=h/15+ra-.06571*t-6.622+lh;val hrs=((local%24)+24)%24
            return (base.clone()as Calendar).apply{set(Calendar.HOUR_OF_DAY,hrs.toInt());set(Calendar.MINUTE,((hrs-hrs.toInt())*60).roundToInt());set(Calendar.SECOND,0);set(Calendar.MILLISECOND,0)}
        }
        return Result(calc(true),calc(false))
    }
}