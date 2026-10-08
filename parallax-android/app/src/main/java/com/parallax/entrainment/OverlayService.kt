package com.parallax.entrainment

import android.app.*
import android.content.*
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.view.Gravity
import android.view.WindowManager
import androidx.core.app.NotificationCompat

class OverlayService : Service() {
    private lateinit var wm: WindowManager
    private var view: EntrainmentSurfaceView? = null
    private var audio: AndroidAudioEngine? = null
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate() {
        super.onCreate()
        wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopOverlay()
            stopSelf()
            return START_NOT_STICKY
        }

        startForeground(NOTIFICATION_ID, notification())

        val p = getSharedPreferences(PREFS, MODE_PRIVATE)
        val full = intent?.getBooleanExtra(EXTRA_IS_FULL_OVERLAY, p.getBoolean(KEY_FULL, false)) ?: false
        val hz = intent?.getFloatExtra(EXTRA_TARGET_HZ, p.getFloat(KEY_HZ, 4f)) ?: 4f
        val seed = intent?.getStringExtra(EXTRA_SEED) ?: p.getString(KEY_SEED, "PARALLAX")!!
        val volume = intent?.getFloatExtra(EXTRA_VOLUME, p.getFloat(KEY_VOLUME, .12f)) ?: .12f
        val fullOpacity = intent?.getFloatExtra(EXTRA_FULL_OPACITY, p.getFloat(KEY_FULL_OPACITY, .75f)) ?: .75f
        val borderWidth = intent?.getFloatExtra(EXTRA_BORDER_WIDTH, p.getFloat(KEY_BORDER_WIDTH, 72f)) ?: 72f
        val borderOpacity = intent?.getFloatExtra(EXTRA_BORDER_OPACITY, p.getFloat(KEY_BORDER_OPACITY, .75f)) ?: .75f

        setupOverlay(full, hz, seed, fullOpacity, borderWidth, borderOpacity)

        audio?.stop()
        audio = AndroidAudioEngine(hz, seed, volume).also { it.start() }

        handler.removeCallbacksAndMessages(null)
        val duration = intent?.getLongExtra(EXTRA_DURATION_MS, 0L) ?: 0L
        if (duration > 0L) {
            handler.postDelayed({
                stopOverlay()
                stopSelf()
            }, duration)
        }

        return START_STICKY
    }

    private fun setupOverlay(
        full: Boolean,
        hz: Float,
        seed: String,
        fullOpacity: Float,
        borderWidth: Float,
        borderOpacity: Float
    ) {
        view?.let { runCatching { wm.removeViewImmediate(it) } }

        val flags =
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
            WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED

        // Keep the overlay window at the Android 15 passthrough-safe alpha.
        // The user-facing full-screen opacity is applied inside the renderer,
        // so the slider does not double-attenuate the window itself.
        val windowOpacity = .75f
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            flags,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            // Android 15 passthrough safety: keep the window <= 0.75 alpha.
            alpha = windowOpacity
            if (Build.VERSION.SDK_INT >= 28) {
                layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            }
        }

        view = EntrainmentSurfaceView(
            this, full, hz, seed,
            fullOpacity.coerceIn(.05f, 1f),
            borderWidth.coerceIn(8f, 240f),
            borderOpacity.coerceIn(0f, 1f)
        )

        try {
            wm.addView(view, params)
        } catch (t: Throwable) {
            view = null
            throw t
        }
    }

    private fun stopOverlay() {
        handler.removeCallbacksAndMessages(null)
        view?.let { runCatching { wm.removeViewImmediate(it) } }
        view = null
        audio?.stop()
        audio = null
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "Parallax Overlay Service",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
    }

    private fun notification(): Notification {
        val settings = PendingIntent.getActivity(
            this, 0, Intent(this, SettingsActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val stop = PendingIntent.getService(
            this, 1, Intent(this, OverlayService::class.java).apply { action = ACTION_STOP },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Parallax Entrainment Active")
            .setContentText("Tap to open settings.")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentIntent(settings)
            .addAction(android.R.drawable.ic_media_pause, "Stop", stop)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        stopOverlay()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val PREFS = "parallax_settings"
        const val KEY_FULL = "full"
        const val KEY_HZ = "hz"
        const val KEY_SEED = "seed"
        const val KEY_VOLUME = "volume"
        const val KEY_FULL_OPACITY = "full_opacity"
        const val KEY_BORDER_WIDTH = "border_width"
        const val KEY_BORDER_OPACITY = "border_opacity"
        const val KEY_SUNSET_SUNRISE = "sunset_sunrise"
        const val KEY_TIMED = "timed"
        const val KEY_TIMED_MINUTES = "timed_minutes"
        const val KEY_DARK_THEME = "dark_theme"

        const val CHANNEL_ID = "parallax_overlay_channel"
        const val NOTIFICATION_ID = 1001
        const val ACTION_STOP = "com.parallax.entrainment.STOP"

        const val EXTRA_IS_FULL_OVERLAY = "EXTRA_IS_FULL_OVERLAY"
        const val EXTRA_TARGET_HZ = "EXTRA_TARGET_HZ"
        const val EXTRA_SEED = "EXTRA_SEED"
        const val EXTRA_VOLUME = "EXTRA_VOLUME"
        const val EXTRA_FULL_OPACITY = "EXTRA_FULL_OPACITY"
        const val EXTRA_BORDER_WIDTH = "EXTRA_BORDER_WIDTH"
        const val EXTRA_BORDER_OPACITY = "EXTRA_BORDER_OPACITY"
        const val EXTRA_DURATION_MS = "EXTRA_DURATION_MS"
    }
}
