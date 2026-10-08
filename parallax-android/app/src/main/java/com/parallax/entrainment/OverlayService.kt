package com.parallax.entrainment

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.view.Gravity
import android.view.WindowManager
import androidx.core.app.NotificationCompat

class OverlayService : Service() {
    private lateinit var windowManager: WindowManager
    private var overlayView: EntrainmentSurfaceView? = null
    private var audioEngine: AndroidAudioEngine? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopOverlay()
            stopSelf()
            return START_NOT_STICKY
        }

        startForeground(NOTIFICATION_ID, buildNotification())

        val full = intent?.getBooleanExtra(EXTRA_IS_FULL_OVERLAY, false) ?: false
        val hz = intent?.getFloatExtra(EXTRA_TARGET_HZ, 4f) ?: 4f
        val seed = intent?.getStringExtra(EXTRA_SEED) ?: "PARALLAX"

        setupOverlayView(full, hz, seed)
        startAudioEngine(hz, seed)
        return START_STICKY
    }

    private fun setupOverlayView(full: Boolean, hz: Float, seed: String) {
        overlayView?.let { runCatching { windowManager.removeView(it) } }
        val type = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        val flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            type,
            flags,
            PixelFormat.TRANSLUCENT
        ).apply { gravity = Gravity.TOP or Gravity.START }

        overlayView = EntrainmentSurfaceView(this, full, hz, seed)
        windowManager.addView(overlayView, params)
    }

    private fun startAudioEngine(hz: Float, seed: String) {
        audioEngine?.stop()
        audioEngine = AndroidAudioEngine(hz, seed).also { it.start() }
    }

    private fun stopOverlay() {
        overlayView?.let { runCatching { windowManager.removeView(it) } }
        overlayView = null
        audioEngine?.stop()
        audioEngine = null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Parallax Overlay Service", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    private fun buildNotification(): Notification {
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
            .setContentText("Tap to open settings. Stop ends the session.")
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
        const val CHANNEL_ID = "parallax_overlay_channel"
        const val NOTIFICATION_ID = 1001
        const val ACTION_STOP = "com.parallax.entrainment.STOP"
        const val EXTRA_IS_FULL_OVERLAY = "EXTRA_IS_FULL_OVERLAY"
        const val EXTRA_TARGET_HZ = "EXTRA_TARGET_HZ"
        const val EXTRA_SEED = "EXTRA_SEED"
    }
}
