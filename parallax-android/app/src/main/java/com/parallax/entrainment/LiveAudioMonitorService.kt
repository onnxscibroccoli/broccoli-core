package com.parallax.entrainment

import android.Manifest
import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.*
import android.os.*
import androidx.core.app.NotificationCompat
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread
import kotlin.math.*

/**
 * Opt-in continuous microphone-versus-actual-Parallax-playback comparison.
 * Only the built-in speaker route qualifies. Headphone/binaural perception cannot
 * be measured through the phone microphone. Never records/stores raw audio.
 */
class LiveAudioMonitorService : Service() {
    private val stopping = AtomicBoolean(false)
    @Volatile private var worker: Thread? = null
    @Volatile private var recorder: AudioRecord? = null
    private var stopReason = "Live monitoring ended."

    override fun onBind(intent: Intent?) = null

    override fun onCreate() {
        super.onCreate()
        AcousticBus.initialize(this)
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel("parallax_live_monitor", "Parallax live microphone comparison",
                NotificationManager.IMPORTANCE_LOW))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopReason = "Live comparison stopped by user."
            stopSelf()
            return START_NOT_STICKY
        }
        if (worker != null || PlaybackReferenceBus.monitorRunning) return START_NOT_STICKY
        if (!PlaybackReferenceBus.sessionPlaying || !PlaybackReferenceBus.builtInSpeaker) {
            PlaybackReferenceBus.status = "Start an audible Parallax session on the built-in speaker first."
            stopSelf(); return START_NOT_STICKY
        }
        if (AcousticBus.calibrating || AcousticBus.polling) {
            PlaybackReferenceBus.status = "Stop room calibration before starting continuous comparison."
            stopSelf(); return START_NOT_STICKY
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            PlaybackReferenceBus.status = "Microphone permission is needed for live comparison."
            stopSelf(); return START_NOT_STICKY
        }
        val stopIntent = PendingIntent.getService(this, 1202,
            Intent(this, LiveAudioMonitorService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val openIntent = PendingIntent.getActivity(this, 1203,
            Intent(this, AcousticSettingsActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = NotificationCompat.Builder(this, "parallax_live_monitor")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("Parallax: continuous speaker comparison")
            .setContentText("Microphone active. Comparing real playback with your generated bells.")
            .setContentIntent(openIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop microphone", stopIntent)
            .setOngoing(true).build()
        try {
            if (Build.VERSION.SDK_INT >= 30)
                startForeground(1202, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            else startForeground(1202, notification)
        } catch (e: RuntimeException) {
            PlaybackReferenceBus.status = "Android blocked microphone foreground service. Open the app and retry."
            stopSelf()
            return START_NOT_STICKY
        }
        PlaybackReferenceBus.monitorRunning = true
        PlaybackReferenceBus.comparisonRequested = true
        PlaybackReferenceBus.meter(null, 0, "Microphone opening; measuring bell/sound similarity...")
        stopping.set(false)
        worker = thread(name = "ParallaxLiveAudioComparison") { monitor() }
        return START_NOT_STICKY // No boot, crash or system restart of microphone.
    }

    private fun monitor() {
        var input: AudioRecord? = null
        try {
            val manager = getSystemService(AudioManager::class.java)
            val mic = manager.getDevices(AudioManager.GET_DEVICES_INPUTS)
                .firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_MIC }
                ?: error("No built-in microphone available.")
            val rate = LiveAudioMatcher.RATE
            val minBytes = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT)
            check(minBytes > 0) { "Device microphone cannot record the required 44.1 kHz format." }
            val unprocessed = manager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true"
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
                throw SecurityException("Microphone permission revoked before capture initialization.")
            input = AudioRecord.Builder()
                .setAudioSource(if (unprocessed) MediaRecorder.AudioSource.UNPROCESSED
                    else MediaRecorder.AudioSource.VOICE_RECOGNITION)
                .setAudioFormat(AudioFormat.Builder().setSampleRate(rate)
                    .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                .setBufferSizeInBytes(max(minBytes, 16384)).build()
            recorder = input
            check(input.state == AudioRecord.STATE_INITIALIZED && input.setPreferredDevice(mic)) {
                "Unable to use the internal microphone."
            }
            input.startRecording()
            val buffer = ShortArray(LiveAudioMatcher.WINDOW)
            var consecutive = 0
            var lastAnalysis = 0L
            var lastCorrection = SystemClock.elapsedRealtime()
            var failures = 0
            while (!stopping.get() && !Thread.currentThread().isInterrupted) {
                if (!PlaybackReferenceBus.sessionPlaying || !PlaybackReferenceBus.builtInSpeaker) {
                    stopReason = "Parallax audio stopped or moved away from its built-in speaker."
                    break
                }
                if (AcousticBus.calibrating || AcousticBus.polling) {
                    stopReason = "Calibration started. Continuous comparison stopped to free the microphone."
                    break
                }
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                    stopReason = "Microphone permission revoked. Comparison stopped."
                    break
                }
                if (manager.mode != AudioManager.MODE_NORMAL) {
                    stopReason = "Call or communication audio started. Comparison stopped."
                    break
                }
                if (getSystemService(PowerManager::class.java).isPowerSaveMode) {
                    stopReason = "Battery saver enabled. Comparison stopped."
                    break
                }
                val battery = getSystemService(BatteryManager::class.java)
                    .getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
                if (battery in 0..15) {
                    stopReason = "Low battery (15% or less). Comparison stopped."
                    break
                }
                val routed = input.routedDevice
                if (routed != null && routed.id != mic.id) {
                    stopReason = "Microphone route changed. Comparison stopped."
                    break
                }
                var filled = 0
                while (filled < buffer.size && !stopping.get()) {
                    val count = input.read(buffer, filled, buffer.size - filled,
                        AudioRecord.READ_BLOCKING)
                    if (count <= 0) {
                        failures++
                        if (failures >= 2) error("Mic returned unavailable samples ($count).")
                        break
                    }
                    filled += count
                }
                if (filled != buffer.size) continue
                failures = 0
                val now = SystemClock.elapsedRealtime()
                if (now - lastAnalysis < 300) continue
                lastAnalysis = now
                val reference = PlaybackReferenceBus.freshSpeakerReference()
                if (reference == null) {
                    PlaybackReferenceBus.meter(null, 0,
                        "Waiting for a fresh speaker reference; headphones and Bluetooth cannot be measured.")
                    consecutive = 0
                    continue
                }
                val match = LiveAudioMatcher.compare(reference.mono, buffer)
                if (!match.valid) {
                    consecutive = 0
                    PlaybackReferenceBus.meter(null, 0, match.reason + ". Microphone remains opt-in.")
                    continue
                }
                if (match.scorePercent >= 78 && match.confidencePercent >= 60)
                    consecutive++ else consecutive = 0
                val auto = AcousticBus.state.liveAutoEq
                PlaybackReferenceBus.meter(match.scorePercent, match.confidencePercent,
                    "Speaker/mic spectral match ${match.scorePercent}%; confidence ${match.confidencePercent}%. " +
                    "${match.activeBands} reference bands; mic/output level ratio " +
                    "${"%.1f".format(match.relativeLevelDb)} dB (uncalibrated); " +
                    "${if (unprocessed) "unprocessed" else "device-processed"} mic. " +
                    (if (auto) "Conservative live EQ enabled." else "Monitor only; EQ unchanged."))
                // Do not continuously chase environmental noise or one-note partials.
                // Manual-locked bands remain authoritative; no upward EQ boosts.
                if (auto && consecutive >= 3 && now - lastCorrection >= 15_000L &&
                    match.correctionDb.count { it != null } >= 4) {
                    val state = AcousticBus.state
                    val next = state.auto.mapIndexed { i, gain ->
                        val estimate = match.correctionDb[i]
                        if (state.locked[i] || estimate == null) gain
                        else (gain + estimate.coerceIn(-.20f, 0f)).coerceIn(-6f, 0f)
                    }
                    if (next != state.auto) AcousticBus.correction(next, false)
                    lastCorrection = now
                    consecutive = 0
                }
            }
        } catch (e: Exception) {
            if (!stopping.get()) {
                stopReason = "Live microphone comparison unavailable: " +
                    (e.message ?: "audio route not supported")
                android.util.Log.w("ParallaxLiveMonitor", "Comparison stopped", e)
            }
        } finally {
            PlaybackReferenceBus.comparisonRequested = false
            val source = recorder
            recorder = null
            runCatching { source?.stop() }
            runCatching { source?.release() }
            PlaybackReferenceBus.monitorRunning = false
            PlaybackReferenceBus.meter(null, 0, stopReason)
            stopSelf()
        }
    }

    override fun onDestroy() {
        stopping.set(true)
        PlaybackReferenceBus.comparisonRequested = false
        runCatching { recorder?.stop() } // unblock READ_BLOCKING
        worker?.interrupt()
        // Keep the monitor busy until the capture worker has released AudioRecord.
        // An immediate new room-calibration request must not race this release.
        super.onDestroy()
    }

    companion object {
        const val ACTION_STOP = "com.parallax.entrainment.LIVE_AUDIO_STOP"
    }
}
