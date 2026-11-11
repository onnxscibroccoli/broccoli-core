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

/** Explicit user-started microphone foreground service; never restarted by boot/scheduler. */
class AcousticService : Service() {
    private val cancelled = AtomicBoolean(false)
    private var worker: Thread? = null
    private val handler = Handler(Looper.getMainLooper())
    private var continuous = false
    override fun onBind(intent: Intent?) = null
    override fun onCreate() {
        super.onCreate()
        AcousticBus.initialize(this)
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel("acoustic", "Acoustic calibration", NotificationManager.IMPORTANCE_LOW))
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "stop") { stopSelf(); return START_NOT_STICKY }
        if (worker != null || AcousticBus.polling) return START_NOT_STICKY
        if (PlaybackReferenceBus.monitorRunning) {
            AcousticBus.status = "Stop continuous speaker comparison before room calibration."
            stopSelf(); return START_NOT_STICKY
        }
        if (AcousticBus.calibrating) { stopSelf(); return START_NOT_STICKY }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            AcousticBus.status = "Microphone permission is required. No correction was changed."
            stopSelf(); return START_NOT_STICKY
        }
        continuous = intent?.getBooleanExtra("continuous", false) == true
        val stop = PendingIntent.getService(this, 40, Intent(this, AcousticService::class.java).setAction("stop"),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val open = PendingIntent.getActivity(this, 41, Intent(this, AcousticSettingsActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = NotificationCompat.Builder(this, "acoustic")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle("Parallax acoustic calibration")
            .setContentText(if (continuous) "40-second audible probes every 10 minutes. Tap Stop to end." else "40-second speaker and microphone test")
            .setContentIntent(open).addAction(0, "Stop", stop).setOngoing(true).build()
        try {
            if (Build.VERSION.SDK_INT >= 29) startForeground(40, notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK or
                    (if (Build.VERSION.SDK_INT >= 30) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE else 0))
            else startForeground(40, notification)
        } catch (_: RuntimeException) {
            AcousticBus.status = "Android could not start microphone capture. Open settings and try again."
            stopSelf(); return START_NOT_STICKY
        }
        AcousticBus.polling = continuous
        launch(false)
        return START_NOT_STICKY
    }
    private fun launch(micro: Boolean) {
        if (cancelled.get()) return
        worker = thread(name = "ParallaxCalibration") {
            try {
                calibrate(micro)
            } catch (_: InterruptedException) {
                AcousticBus.status = "Calibration stopped. Previous correction retained."
            } catch (e: Exception) {
                AcousticBus.status = "Calibration not applied: ${e.message ?: "audio device unavailable"}"
                android.util.Log.w("ParallaxAcoustics", "Calibration failed", e)
                continuous = false
            } finally {
                AcousticBus.calibrating = false
                handler.post {
                    worker = null
                    if (!cancelled.get() && continuous) {
                        AcousticBus.status += " Next check in 10 minutes; microphone released between checks."
                        handler.postDelayed({
                            val power = getSystemService(PowerManager::class.java)
                            val battery = getSystemService(BatteryManager::class.java)
                            if (power.isPowerSaveMode || battery.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) in 0..15) {
                                AcousticBus.status = "Auto-polling stopped to save battery. Enable again when ready."
                                stopSelf()
                            } else launch(true)
                        }, 600_000L)
                    } else stopSelf()
                }
            }
        }
    }
    private fun calibrate(micro: Boolean) {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
            throw SecurityException("Microphone permission revoked")
        val manager = getSystemService(AudioManager::class.java)
        val speaker = manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS).firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER }
            ?: error("Built-in speaker unavailable")
        val mic = manager.getDevices(AudioManager.GET_DEVICES_INPUTS).firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_MIC }
            ?: error("Built-in microphone unavailable")
        val volume = manager.getStreamVolume(AudioManager.STREAM_MUSIC)
        check(volume > 0) { "Raise media volume to a comfortable level and retry" }
        check(manager.mode == AudioManager.MODE_NORMAL) { "End the active call before calibration" }
        val rate = 44100
        val minimum = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        check(minimum > 0) { "Microphone format unsupported" }
        var record: AudioRecord? = null
        var track: AudioTrack? = null
        AcousticBus.calibrating = true
        try {
            // Give the existing generator time to fade down before measuring the noise floor.
            Thread.sleep(200)
            val unprocessed = manager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true"
            record = AudioRecord.Builder()
                .setAudioSource(if (unprocessed) MediaRecorder.AudioSource.UNPROCESSED else MediaRecorder.AudioSource.VOICE_RECOGNITION)
                .setAudioFormat(AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                .setBufferSizeInBytes(max(minimum, 16384)).build()
            check(record.state == AudioRecord.STATE_INITIALIZED && record.setPreferredDevice(mic)) { "Microphone initialization failed" }
            track = AudioTrack.Builder().setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                .setAudioFormat(AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .setEncoding(AudioFormat.ENCODING_PCM_FLOAT).build())
                .setBufferSizeInBytes(8192).setTransferMode(AudioTrack.MODE_STREAM).build()
            check(track.state == AudioTrack.STATE_INITIALIZED && track.setPreferredDevice(speaker)) { "Speaker initialization failed" }
            record.startRecording(); track.play()
            val noise = DoubleArray(7); val signal = DoubleArray(7); val counts = IntArray(8)
            val capture = ShortArray(2048); var captured = 0
            val output = FloatArray(512); var offset = output.size
            var phase = 0.0; var previousStage = -1; var clipped = 0L; var total = 0L
            val start = SystemClock.elapsedRealtime()
            while (true) {
                if (cancelled.get() || Thread.currentThread().isInterrupted) throw InterruptedException()
                val elapsed = SystemClock.elapsedRealtime() - start
                if (elapsed >= 40000) break
                check(manager.getStreamVolume(AudioManager.STREAM_MUSIC) == volume) { "Media volume changed; please retry" }
                check(manager.mode == AudioManager.MODE_NORMAL) { "Audio interrupted by call" }
                val stage = (elapsed / 5000).toInt()
                if (stage != previousStage) {
                    captured = 0; previousStage = stage
                    android.util.Log.i("ParallaxAcoustics", "Calibration stage $stage/7")
                }
                AcousticBus.status = "Calibrating ${elapsed / 1000}/40 s — " +
                    if (stage == 0) "ambient noise" else "${AcousticDsp.bands[stage - 1].toInt()} Hz"
                if (offset == output.size) {
                    val frequency = if (stage == 0) 0.0 else AcousticDsp.bands[stage - 1]
                    for (i in output.indices) {
                        val within = elapsed % 5000 + i * 1000.0 / rate
                        val ramp = min(min(within / 100, (5000 - within) / 100), 1.0).coerceAtLeast(0.0)
                        output[i] = (sin(phase) * .10 * ramp).toFloat()
                        phase = (phase + 2 * PI * frequency / rate) % (2 * PI)
                    }
                    offset = 0
                }
                val written = track.write(output, offset, output.size - offset, AudioTrack.WRITE_NON_BLOCKING)
                check(written >= 0) { "Speaker write failed ($written)" }; offset += written
                val read = record.read(capture, captured, capture.size - captured, AudioRecord.READ_NON_BLOCKING)
                check(read >= 0) { "Microphone read failed ($read)" }; captured += read
                if (elapsed % 5000 > 1000) {
                    check(track.routedDevice?.id == speaker.id && record.routedDevice?.id == mic.id) { "Audio route changed or is not built-in" }
                }
                if (captured == capture.size) {
                    if (elapsed % 5000 in 1200..4700) {
                        clipped += capture.count { abs(it.toInt()) >= 32000 }; total += capture.size
                        if (stage == 0) for (i in noise.indices) noise[i] += AcousticDsp.power(capture, captured, AcousticDsp.bands[i], rate)
                        else signal[stage - 1] += AcousticDsp.power(capture, captured, AcousticDsp.bands[stage - 1], rate)
                        counts[stage]++
                    }
                    captured = 0
                }
                Thread.sleep(4)
            }
            check(counts.all { it >= 10 } && total > 0) { "Insufficient microphone samples" }
            val clipPercent = clipped.toDouble() * 100.0 / total
            check(clipPercent < .5) {
                "Mic clipped (${"%.2f".format(clipPercent)}%). Lower media volume and retry; previous EQ retained."
            }
            val noisePower = noise.map { it / counts[0] }
            val signalPower = signal.mapIndexed { i, v -> v / counts[i + 1] }
            val adaptive = AcousticDsp.adaptiveCorrection(noisePower, signalPower)
                ?: error("Insufficient clear test bands (need 4/7). Move away from noise, raise media volume one step at a time, or try a different orientation. Original EQ retained.")
            if (cancelled.get()) throw InterruptedException()
            val current = AcousticBus.state.auto
            // Keep the previous EQ in weak bands. Auto-polling still limits gain steps.
            val target = adaptive.bands.mapIndexed { i, correction -> correction ?: current[i] }
            AcousticBus.correction(target, micro)
            AcousticDsp.normalizedSpectrum(noisePower, signalPower)
                ?.let { AcousticBus.sonarReading(it) }
            AcousticBus.status =
                "Correction applied using ${adaptive.validCount}/7 valid bands; " +
                if (adaptive.weakHz.isEmpty()) "all bands measured."
                else "weak bands ${adaptive.weakHz.joinToString()} Hz preserved."
        } finally {
            runCatching { record?.stop() }; runCatching { record?.release() }
            runCatching { track?.pause() }; runCatching { track?.flush() }; runCatching { track?.release() }
        }
    }
    override fun onDestroy() {
        cancelled.set(true); worker?.interrupt()
        handler.removeCallbacksAndMessages(null)
        AcousticBus.polling = false
        // Worker alone owns audio resources and clears calibrating after releasing them.
        super.onDestroy()
    }
}
