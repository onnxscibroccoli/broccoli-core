package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.media.*
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.*
import kotlin.concurrent.thread
import kotlin.math.*

/**
 * Single-device opt-in experimental sonar. One chirp probe while visible;
 * no continuous background mic, upload, persistent PCM, or unsupported maps.
 */
class ActiveSonarActivity : Activity(), SensorEventListener {
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var runButton: Button
    private lateinit var sensorManager: SensorManager
    private var previousYaw: Float? = null
    private var previousGyroTimestampNs = 0L
    @Volatile private var relativeYawDegrees = 0f
    @Volatile private var motionObserved = false
    @Volatile private var cancelled = false
    @Volatile private var worker: Thread? = null
    @Volatile private var recorder: AudioRecord? = null
    @Volatile private var speaker: AudioTrack? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sensorManager = getSystemService(SensorManager::class.java)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 64, 32, 64)
        }
        setContentView(ScrollView(this).apply { addView(panel) })
        fun text(s: String): TextView = TextView(this).apply {
            text = s; textSize = 17f; setPadding(0, 16, 0, 16); panel.addView(this)
        }
        text("Single-Phone Active Acoustic Sensing").textSize = 24f
        text("An explicitly started 20 ms 17.5–21.5 kHz chirp tests your own speaker and microphone. Some children and animals may hear near-ultrasound. Keep media volume comfortable. No sound recording is stored or transmitted.")
        text("This is a prototype measuring a candidate reflection relative to direct speaker-to-microphone leakage. A single microphone cannot determine direction or distinguish a person from a wall; results may be invalid on low-cost phone hardware.")
        runButton = Button(this).apply {
            text = "Measure one acoustic echo (about 1 second)"
            setOnClickListener { confirmProbe() }
        }
        panel.addView(runButton)
        status = text("Ready. Microphone is OFF. No measurements yet.").apply {
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        text("The IMU supplies device orientation change and a motion-warning flag, NOT drift-free position. A calibrated spatial map and background presence detection are not yet implemented.")
        panel.addView(Button(this).apply { text = "Stop / back"; setOnClickListener { stopProbe(); finish() } })
    }

    private fun confirmProbe() {
        if (worker?.isAlive == true) return
        AlertDialog.Builder(this).setTitle("Run a near-ultrasound measurement?")
            .setMessage("Keep the phone still, away from ears and animals. Only the built-in speaker and microphone are used. No PCM or positional history is saved. Press Cancel to leave the microphone off.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Measure") { _, _ ->
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
                    requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 44)
                else startProbe()
            }.show()
    }
    override fun onRequestPermissionsResult(code: Int, perms: Array<out String>, grants: IntArray) {
        super.onRequestPermissionsResult(code, perms, grants)
        if (code == 44 && grants.firstOrNull() == PackageManager.PERMISSION_GRANTED) startProbe()
        else if (code == 44) status.text = "Microphone permission denied. No acoustic probe ran."
    }
    private fun startProbe() {
        if (worker?.isAlive == true) return
        cancelled = false; motionObserved = false
        runButton.isEnabled = false
        status.text = "Opening audio devices; microphone will be active for about one second..."
        worker = thread(name = "ParallaxSingleEchoProbe") {
            try {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
                    error("Microphone permission revoked.")
                val manager = getSystemService(AudioManager::class.java)
                check(manager.mode == AudioManager.MODE_NORMAL) { "Finish calls before testing." }
                check(manager.getStreamVolume(AudioManager.STREAM_MUSIC) > 0) {
                    "Set a low comfortable media volume first."
                }
                val mic = manager.getDevices(AudioManager.GET_DEVICES_INPUTS)
                    .firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_MIC }
                    ?: error("No internal microphone accessible.")
                val out = manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
                    .firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER }
                    ?: error("No internal speaker accessible.")
                val rate = FmcwSonarDsp.RATE
                val minIn = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT)
                val minOut = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT)
                check(minIn > 0 && minOut > 0) { "48 kHz audio route not supported." }
                val unprocessed = manager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true"
                val input = AudioRecord.Builder()
                    .setAudioSource(if (unprocessed) MediaRecorder.AudioSource.UNPROCESSED else MediaRecorder.AudioSource.VOICE_RECOGNITION)
                    .setAudioFormat(AudioFormat.Builder().setSampleRate(rate)
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setChannelMask(AudioFormat.CHANNEL_IN_MONO).build())
                    .setBufferSizeInBytes(max(minIn, 8192)).build()
                recorder = input
                check(input.state == AudioRecord.STATE_INITIALIZED && input.setPreferredDevice(mic)) {
                    "Microphone initialization or internal route failed."
                }
                val output = AudioTrack.Builder()
                    .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build())
                    .setAudioFormat(AudioFormat.Builder().setSampleRate(rate)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                    .setBufferSizeInBytes(max(minOut, 4096))
                    .setTransferMode(AudioTrack.MODE_STREAM).build()
                speaker = output
                check(output.state == AudioTrack.STATE_INITIALIZED && output.setPreferredDevice(out)) {
                    "Speaker initialization or internal route failed."
                }
                val tone = FmcwSonarDsp.chirp()
                val chirp = ShortArray(tone.size) { (tone[it] * .055 * 32767).toInt().toShort() }
                val capture = ShortArray(rate)
                input.startRecording()
                val send = thread(name = "ParallaxChirpPlayback") {
                    try {
                        Thread.sleep(150)
                        if (!cancelled) {
                            output.play()
                            val written = output.write(chirp, 0, chirp.size, AudioTrack.WRITE_BLOCKING)
                            if (written != chirp.size) android.util.Log.w("ParallaxSonar", "Incomplete chirp playback")
                        }
                    } catch (_: Exception) { /* Receiver reports absent signal safely. */ }
                }
                var cursor = 0
                while (cursor < capture.size && !cancelled) {
                    val read = input.read(capture, cursor, min(4096, capture.size - cursor),
                        AudioRecord.READ_BLOCKING)
                    if (read <= 0) error("Microphone read failure: " + read)
                    cursor += read
                }
                send.join(1200)
                if (cancelled) return@thread
                check(input.routedDevice?.id == mic.id && output.routedDevice?.id == out.id) {
                    "Audio route changed. Disconnect other output devices and try again."
                }
                val result = FmcwSonarDsp.estimate(FloatArray(cursor) { capture[it] / 32768f })
                // PCM is discarded after the local calculation.
                ui.post {
                    if (cancelled) return@post
                    status.text = if (result == null)
                        "No reliable direct-and-echo pair. This can happen with a filtered or weak phone microphone, acoustic interference, or no reflecting target. No distance inferred. Try a quiet room or device orientation."
                    else
                        "Candidate reflection: %.2f m relative to the speaker/mic leakage path; echo correlation %.2f. Approximate device heading change: %.0f°. %s NOT a verified spatial position."
                            .format(result.rangeMeters, result.echoCorrelation, relativeYawDegrees,
                                if (motionObserved) "Device moved during probe; low confidence." else "Device appeared still.")
                    result?.let { AcousticBus.sonarEcho(it.rangeMeters.toFloat(), it.echoCorrelation.toFloat()) }
                }
            } catch (e: Exception) {
                ui.post { if (!cancelled) status.text = "Probe not applied: " + (e.message ?: "audio unavailable") }
            } finally {
                val input = recorder; recorder = null
                val output = speaker; speaker = null
                runCatching { input?.stop() }; runCatching { input?.release() }
                runCatching { output?.pause() }; runCatching { output?.flush() }
                runCatching { output?.release() }
                ui.post { runButton.isEnabled = true }
            }
        }
    }

    private fun stopProbe() {
        cancelled = true
        worker?.interrupt()
        runCatching { recorder?.stop() }
        runCatching { speaker?.pause() }
    }
    override fun onResume() {
        super.onResume()
        previousGyroTimestampNs = 0L
        val rotation = sensorManager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR)
        val gyro = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        val accel = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        if (rotation != null) sensorManager.registerListener(this, rotation, SensorManager.SENSOR_DELAY_GAME)
        else if (gyro != null) sensorManager.registerListener(this, gyro, SensorManager.SENSOR_DELAY_GAME)
        if (accel != null) sensorManager.registerListener(this, accel, SensorManager.SENSOR_DELAY_GAME)
    }
    override fun onPause() {
        stopProbe()
        sensorManager.unregisterListener(this)
        super.onPause()
    }
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_GAME_ROTATION_VECTOR -> {
                val matrix = FloatArray(9); val angles = FloatArray(3)
                SensorManager.getRotationMatrixFromVector(matrix, event.values)
                SensorManager.getOrientation(matrix, angles)
                val yaw = Math.toDegrees(angles[0].toDouble()).toFloat()
                if (previousYaw == null) previousYaw = yaw
                relativeYawDegrees = (yaw - (previousYaw ?: yaw) + 540f) % 360f - 180f
            }
            Sensor.TYPE_GYROSCOPE -> {
                // Relative-only fallback when Android does not expose a fused
                // GAME_ROTATION_VECTOR. Drift accumulates; never use as absolute position.
                if (previousGyroTimestampNs > 0L && event.timestamp > previousGyroTimestampNs) {
                    val dt = ((event.timestamp - previousGyroTimestampNs) / 1e9).coerceIn(0.0, 0.1)
                    val degrees = Math.toDegrees(event.values[2].toDouble() * dt).toFloat()
                    relativeYawDegrees = (relativeYawDegrees + degrees + 540f) % 360f - 180f
                }
                previousGyroTimestampNs = event.timestamp
            }
            Sensor.TYPE_ACCELEROMETER -> {
                val magnitude = sqrt(event.values.sumOf { (it * it).toDouble() })
                if (worker?.isAlive == true && abs(magnitude - 9.81) > 2.0) motionObserved = true
            }
        }
    }
}
