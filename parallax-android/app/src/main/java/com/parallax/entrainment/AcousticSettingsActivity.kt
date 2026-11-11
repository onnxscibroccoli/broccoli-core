package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.*
import android.view.View
import android.widget.*

class AcousticSettingsActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var monitor: Switch
    private lateinit var monitorStatus: TextView
    private lateinit var calibrate: Button
    private val labels = mutableListOf<TextView>()
    private val sliders = mutableListOf<SeekBar>()
     private val refresh = object : Runnable {
        override fun run() {
            if (status.text.toString() != AcousticBus.status) status.text = AcousticBus.status
            monitor.isChecked = PlaybackReferenceBus.monitorRunning
            val info = PlaybackReferenceBus.status
            if (monitorStatus.text.toString() != info) monitorStatus.text = info
            calibrate.isEnabled = !AcousticBus.calibrating && !PlaybackReferenceBus.monitorRunning
            val state = AcousticBus.state
            for (i in labels.indices) {
                labels[i].text = "${AcousticDsp.bands[i].toInt()} Hz: %.1f dB (%s); base %.1f dB".format(
                    state.effective[i], if (state.locked[i]) "manual" else "auto", state.auto[i])
                if (!sliders[i].isPressed) sliders[i].progress = ((state.effective[i] + 12) * 2).toInt()
            }
            handler.postDelayed(this, 500)
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AcousticBus.initialize(this)
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(32, 40, 32, 40) }
        setContentView(ScrollView(this).apply { addView(box) })
        // Respect system bars, including Android 15 edge-to-edge enforcement.
        box.setOnApplyWindowInsetsListener { view, insets ->
            @Suppress("DEPRECATION")
            view.setPadding(32 + insets.systemWindowInsetLeft, 24 + insets.systemWindowInsetTop,
                32 + insets.systemWindowInsetRight, 24 + insets.systemWindowInsetBottom)
            insets
        }
        fun text(value: String) = TextView(this).apply { text = value; textSize = 16f; setPadding(0, 16, 0, 16); box.addView(this) }
        text("Acoustic & Healing Profiles").textSize = 24f
        text("Bell profiles are listening presets, not medical treatments. Enable session audio in the main settings to hear them. Audio analysis stays on this device; recordings are never saved.")
        box.addView(Switch(this).apply {
            text = "Enable Bell Profiles"; minHeight = 64; isChecked = AcousticBus.state.bells
            setOnCheckedChangeListener { _, value ->
                AcousticBus.bells(value)
                if (value) {
                    val p = getSharedPreferences(OverlayService.PREFS, MODE_PRIVATE)
                    if (p.getInt(OverlayService.KEY_AUDIO_MODE, OverlayService.AUDIO_MODE_MIX) == OverlayService.AUDIO_MODE_OFF) {
                        p.edit().putInt(OverlayService.KEY_AUDIO_MODE, OverlayService.AUDIO_MODE_MIX).apply()
                        if (p.getBoolean(OverlayService.KEY_SESSION_ACTIVE, false))
                            startForegroundService(Intent(this@AcousticSettingsActivity, OverlayService::class.java)
                                .setAction(OverlayService.ACTION_UPDATE))
                        AcousticBus.status = "Bell playback enabled in Play Alongside mode. Start a session to hear it."
                    }
                }
            }
        })
        text("Binaural mode requires stereo headphones. On the phone speaker you hear the sound, but not the interaural binaural beat. The chosen beat rate comes from the main screen's target frequency.")
        box.addView(Switch(this).apply {
            text = "Bells as binaural carrier (rather than a soft layer)"
            minHeight = 64; isChecked = AcousticBus.state.bellCarrier
            setOnCheckedChangeListener { _, value -> AcousticBus.bellCarrier(value) }
        })
        box.addView(Switch(this).apply {
            text = "Long ringing bowl timbre (paired modal resonances)"
            minHeight = 64; isChecked = AcousticBus.state.bowlMode
            setOnCheckedChangeListener { _, value -> AcousticBus.bowlMode(value) }
        })
        box.addView(Switch(this).apply {
            text = "Hourly bell chime during an active audio session"
            minHeight = 64; isChecked = AcousticBus.state.hourlyChime
            setOnCheckedChangeListener { _, value -> AcousticBus.hourlyChime(value) }
        })
        text("Chimes trigger at the top of each hour only while an audio session is already playing. Android will not start the microphone, an overlay, or a stopped session to ring.")
        val ringLabel = text("Bell sustain: ${AcousticBus.state.bellRingSeconds} seconds")
        box.addView(SeekBar(this).apply {
            max = 58; progress = AcousticBus.state.bellRingSeconds - 2
            contentDescription = "Bell sustain duration in seconds"
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onStartTrackingTouch(bar: SeekBar?) {}
                override fun onStopTrackingTouch(bar: SeekBar?) {}
                override fun onProgressChanged(bar: SeekBar?, value: Int, fromUser: Boolean) {
                    if (fromUser) { AcousticBus.bellRingSeconds(value + 2); ringLabel.text = "Bell sustain: ${value + 2} seconds" }
                }
            })
        })
        val intervalLabel = text("Bell repeat interval: ${AcousticBus.state.bellIntervalSeconds} seconds")
        box.addView(SeekBar(this).apply {
            max = 296; progress = AcousticBus.state.bellIntervalSeconds - 4
            contentDescription = "Bell repeat interval in seconds"
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onStartTrackingTouch(bar: SeekBar?) {}
                override fun onStopTrackingTouch(bar: SeekBar?) {}
                override fun onProgressChanged(bar: SeekBar?, value: Int, fromUser: Boolean) {
                    if (fromUser) { AcousticBus.bellIntervalSeconds(value + 4); intervalLabel.text = "Bell repeat interval: ${value + 4} seconds" }
                }
            })
        })
        text("Bell frequency")
        box.addView(Spinner(this).apply {
            contentDescription = "Healing bell frequency profile"
            adapter = ArrayAdapter(this@AcousticSettingsActivity, android.R.layout.simple_spinner_dropdown_item,
                AcousticDsp.bells.map { "${it.toInt()} Hz bell" })
            setSelection(AcousticBus.state.profile)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) { AcousticBus.profile(position) }
            }
        })
        text("Keep the phone still in a quiet room. Calibration plays 40 seconds of low-level test tones through its speaker, briefly muting session tones. Results approximate the combined speaker, room and microphone response. Deep nulls are not boosted. Automatic correction applies only on the built-in speaker.")
        calibrate = Button(this).apply {
            text = "Calibrate Room & Speakers (40s)"
            setOnClickListener { requestCalibration(false) }
        }; box.addView(calibrate)
        text("Continuous microphone-to-bell comparison").textSize = 20f
        text("Start an audible session on the phone speaker first. After explicit consent, the microphone continuously compares its captured spectral profile against the actual Parallax bell/binaural signal after EQ and volume processing, roughly every 300 ms. It is not a 10-minute test-tone sweep. Headphones and Bluetooth cannot be verified by the phone microphone.")
        monitor = Switch(this).apply {
            text = "Continuous speaker/microphone comparison"; minHeight = 64
            isChecked = PlaybackReferenceBus.monitorRunning
            setOnClickListener {
                if (isChecked) LiveMonitorUi.confirmStart(this@AcousticSettingsActivity)
                else LiveMonitorUi.stop(this@AcousticSettingsActivity)
            }
        }; box.addView(monitor)
        box.addView(Switch(this).apply {
            text = "Optional conservative live Auto EQ (cut peaks only)"
            minHeight = 64; isChecked = AcousticBus.state.liveAutoEq
            setOnCheckedChangeListener { _, enabled -> AcousticBus.liveAutoEq(enabled) }
        })
        text("Live EQ adjusts at most 0.2 dB per eligible band every 15 seconds after repeated confident broadband matches. Weak, clipped, or one-note input is monitor-only. Manual EQ locks always win. Comparison stops if session/route ends or battery saver activates. It does not restart automatically.")
        monitorStatus = text(PlaybackReferenceBus.status).apply {
            // Status stays focusable/readable without incessant TalkBack announcements.
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_NONE
        }
        box.addView(Button(this).apply {
            text = "Stop live microphone comparison"
            setOnClickListener { LiveMonitorUi.stop(this@AcousticSettingsActivity) }
        })
        box.addView(Button(this).apply {
            text = "Stop room calibration"
            setOnClickListener {
                stopService(Intent(this@AcousticSettingsActivity, AcousticService::class.java))
                AcousticBus.status = "Stopping room calibration."
            }
        })
        status = text(AcousticBus.status).apply { accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        text("Manual Equalizer Override — moving a slider locks that band. Other bands remain automatic. Changes are smoothed over roughly 200 ms to avoid clicks.")
        for (i in AcousticDsp.bands.indices) {
            labels += text("")
            val slider = SeekBar(this).apply {
                max = 36; progress = ((AcousticBus.state.effective[i] + 12) * 2).toInt()
                contentDescription = "${AcousticDsp.bands[i].toInt()} Hz gain, minus 12 to plus 6 decibels"
                minimumHeight = 64
                setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                    override fun onStartTrackingTouch(bar: SeekBar?) {}
                    override fun onStopTrackingTouch(bar: SeekBar?) {}
                    override fun onProgressChanged(bar: SeekBar?, value: Int, fromUser: Boolean) {
                        if (fromUser) AcousticBus.manual(i, value / 2f - 12)
                    }
                })
            }
            sliders += slider; box.addView(slider)
        }
        box.addView(Button(this).apply { text = "Return all bands to automatic"; setOnClickListener { AcousticBus.resetManual() } })

        // Playback-driven Parallax effect: independent from the room-test sonar.
        text("Audio-reactive Parallax Distortion").textSize = 20f
        text("Audio-reactive mode gently increases the original color-field entities' distance from the center, radius and glow according to the amplitude actually written by Parallax. It does not add sonar rings, strobe, or capture the microphone.")
        box.addView(Switch(this).apply {
            text = "Enable audio-reactive Parallax visuals"
            minHeight = 64; isChecked = AcousticBus.state.audioVisualEnabled
            setOnCheckedChangeListener { _, checked -> AcousticBus.audioVisual(checked) }
        })
        val reactiveLabel = text("Visual audio response: ${(AcousticBus.state.audioVisualStrength * 100).toInt()}%")
        box.addView(SeekBar(this).apply {
            max = 100; progress = (AcousticBus.state.audioVisualStrength * 100).toInt()
            contentDescription = "Audio-reactive visual strength"
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onStartTrackingTouch(bar: SeekBar?) {}
                override fun onStopTrackingTouch(bar: SeekBar?) {}
                override fun onProgressChanged(bar: SeekBar?, value: Int, fromUser: Boolean) {
                    if (fromUser) {
                        AcousticBus.audioVisualStrength(value / 100f)
                        reactiveLabel.text = "Visual audio response: ${value}%"
                    }
                }
            })
        })

        // v2.1 Sonar Overlay controls (completely independent)
        text("Room-test sonar visualization (separate)").textSize = 20f
        text("The separate sonar-themed rings show room-test spectral data and any candidate echo from the manually initiated room probe. This is independent of the playback-reactive Parallax blobs and does not start the microphone.")
        box.addView(Switch(this).apply {
            text = "Enable Acoustic Sonar Overlay"; minHeight = 64; isChecked = AcousticBus.state.sonarEnabled
            setOnCheckedChangeListener { _, value -> AcousticBus.sonar(value) }
        })
        text("Sonar Ring Intensity")
        box.addView(SeekBar(this).apply {
            max = 100
            progress = (AcousticBus.state.sonarSensitivity * 100).toInt()
            contentDescription = "Sonar sensitivity, 0 to 100 percent"
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onStartTrackingTouch(bar: SeekBar?) {}
                override fun onStopTrackingTouch(bar: SeekBar?) {}
                override fun onProgressChanged(bar: SeekBar?, value: Int, fromUser: Boolean) {
                    if (fromUser) AcousticBus.sonarSensitivity(value / 100f)
                }
            })
        })

        box.addView(Button(this).apply { text = "Back to settings"; setOnClickListener { finish() } })
        if (intent.getBooleanExtra("start_calibration", false)) {
            handler.post { requestCalibration(false) }
        }
    }
    private fun requestCalibration(continuous: Boolean) {
        if (AcousticBus.calibrating || AcousticBus.polling || PlaybackReferenceBus.monitorRunning) {
            AcousticBus.status = "Stop live comparison before room calibration."
            return
        }
        AlertDialog.Builder(this).setTitle("Start 40-second room calibration?")
            .setMessage("Use a comfortable media volume and keep the phone still. The microphone measures test tones locally. Existing EQ is retained if measurement fails.")
            .setNegativeButton("Cancel", null).setPositiveButton("Start") { _, _ ->
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
                    requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 40)
                else begin()
            }.show()
    }
    private fun begin() {
        try {
            startForegroundService(Intent(this, AcousticService::class.java).putExtra("continuous", false))
        } catch (_: RuntimeException) {
            AcousticBus.status = "Unable to start microphone service. Open this screen and retry."
        }
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (LiveMonitorUi.onPermissionResult(this, requestCode, grantResults)) return
        if (requestCode == 40 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) begin()
        else if (requestCode == 40)
            AcousticBus.status = "Microphone permission denied. Bell profiles and manual EQ remain available."
    }
    override fun onResume() { super.onResume(); handler.post(refresh) }
    override fun onPause() { handler.removeCallbacks(refresh); super.onPause() }
}
