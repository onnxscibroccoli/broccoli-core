package com.parallax.entrainment

import android.Manifest
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.*
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.provider.Settings
import java.util.Calendar
import kotlin.math.*

class ScheduleReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val p = context.getSharedPreferences(OverlayService.PREFS, Context.MODE_PRIVATE)
        when (intent?.action) {
            ACTION_SUNSET -> startAtSunset(context)
            ACTION_SUNRISE -> stopAtSunrise(context)
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED -> if (p.getBoolean(OverlayService.KEY_SUNSET_SUNRISE, false)) {
                reschedule(context)
            }
        }
    }

    private fun startAtSunset(context: Context) {
        if (!Settings.canDrawOverlays(context)) return
        val start = Intent(context, OverlayService::class.java)
        if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(start) else context.startService(start)
        reschedule(context)
    }

    private fun stopAtSunrise(context: Context) {
        context.stopService(Intent(context, OverlayService::class.java))
        reschedule(context)
    }

    companion object {
        const val ACTION_SUNSET = "com.parallax.entrainment.SUNSET"
        const val ACTION_SUNRISE = "com.parallax.entrainment.SUNRISE"
        private const val REQUEST_SUNSET = 7001
        private const val REQUEST_SUNRISE = 7002
        private const val DAY_MS = 86_400_000L

        fun reschedule(context: Context) {
            val prefs = context.getSharedPreferences(OverlayService.PREFS, Context.MODE_PRIVATE)
            val alarms = context.getSystemService(AlarmManager::class.java)

            alarms.cancel(pending(context, ACTION_SUNSET, REQUEST_SUNSET))
            alarms.cancel(pending(context, ACTION_SUNRISE, REQUEST_SUNRISE))

            if (!prefs.getBoolean(OverlayService.KEY_SUNSET_SUNRISE, false)) return

            val location = lastKnownLocation(context) ?: return
            val now = System.currentTimeMillis()
            val times = SunTimes.forDate(location.latitude, location.longitude, Calendar.getInstance())

            alarms.setAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                nextAfterNow(now, times.sunset),
                pending(context, ACTION_SUNSET, REQUEST_SUNSET)
            )
            alarms.setAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                nextAfterNow(now, times.sunrise),
                pending(context, ACTION_SUNRISE, REQUEST_SUNRISE)
            )
        }

        private fun pending(context: Context, action: String, request: Int): PendingIntent =
            PendingIntent.getBroadcast(
                context,
                request,
                Intent(context, ScheduleReceiver::class.java).setAction(action),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )

        private fun nextAfterNow(now: Long, time: Calendar): Long =
            if (time.timeInMillis > now) time.timeInMillis else time.timeInMillis + DAY_MS

        private fun lastKnownLocation(context: Context): Location? {
            if (Build.VERSION.SDK_INT >= 23 &&
                context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED
            ) return null

            val manager = context.getSystemService(LocationManager::class.java)
            return listOf(LocationManager.NETWORK_PROVIDER, LocationManager.GPS_PROVIDER)
                .mapNotNull { runCatching { manager.getLastKnownLocation(it) }.getOrNull() }
                .maxByOrNull { it.time }
        }
    }
}

object SunTimes {
    data class Result(val sunrise: Calendar, val sunset: Calendar)

    fun forDate(latitude: Double, longitude: Double, base: Calendar): Result {
        fun calculate(rising: Boolean): Calendar {
            val dayOfYear = base.get(Calendar.DAY_OF_YEAR)
            val longitudeHour = longitude / 15.0
            val approx = dayOfYear + ((if (rising) 6.0 else 18.0) - longitudeHour) / 24.0
            val meanAnomaly = .9856 * approx - 3.289

            var trueLongitude =
                meanAnomaly +
                1.916 * sin(Math.toRadians(meanAnomaly)) +
                .020 * sin(Math.toRadians(2 * meanAnomaly)) +
                282.634
            trueLongitude = (trueLongitude % 360 + 360) % 360

            var rightAscension = Math.toDegrees(
                atan(.91764 * tan(Math.toRadians(trueLongitude)))
            )
            rightAscension = (rightAscension % 360 + 360) % 360
            rightAscension +=
                (floor(trueLongitude / 90) * 90 - floor(rightAscension / 90) * 90) / 15

            val sinDeclination = .39782 * sin(Math.toRadians(trueLongitude))
            val cosDeclination = cos(asin(sinDeclination))
            val cosHourAngle =
                (cos(Math.toRadians(90.833)) -
                    sin(Math.toRadians(latitude)) * sinDeclination) /
                    (cos(Math.toRadians(latitude)) * cosDeclination)

            // Polar day/night: there is no valid transition on this date.
            if (cosHourAngle > 1.0 || cosHourAngle < -1.0) {
                return (base.clone() as Calendar).apply {
                    timeInMillis = if (rising) Long.MAX_VALUE else Long.MAX_VALUE
                }
            }

            val hourAngle = if (rising)
                360 - Math.toDegrees(acos(cosHourAngle))
            else
                Math.toDegrees(acos(cosHourAngle))

            val localSolarTime =
                hourAngle / 15 + rightAscension - .06571 * approx - 6.622 + longitudeHour

            // NOAA's solar-time equation is UTC based. Convert to device local time.
            val utcHours = ((localSolarTime % 24) + 24) % 24
            val offsetHours = base.timeZone.getOffset(base.timeInMillis) / 3_600_000.0
            val localHours = ((utcHours + offsetHours) % 24 + 24) % 24

            return (base.clone() as Calendar).apply {
                set(Calendar.HOUR_OF_DAY, localHours.toInt())
                set(Calendar.MINUTE, ((localHours - localHours.toInt()) * 60).roundToInt().coerceIn(0, 59))
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
        }

        return Result(calculate(true), calculate(false))
    }
}
