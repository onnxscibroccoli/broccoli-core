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
    private lateinit var polling: Switch
    private lateinit var calibrate: Button
    private val labels = mutableListOf<TextView>()
    private val sliders = mutableListOf<SeekBar>()
    private var pendingContinuous = false
    private val refresh = object : Runnable {
        override fun run() {
            if (status.text.toString() != AcousticBus.status) status.text = AcousticBus.status
            polling.isChecked = AcousticBus.polling
            calibrate.isEnabled = !AcousticBus.calibrating && !AcousticBus.polling
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
            text = "Enable Healing Bell Profiles"; minHeight = 64; isChecked = AcousticBus.state.bells
            setOnCheckedChangeListener { _, value -> AcousticBus.bells(value) }
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
        polling = Switch(this).apply {
            text = "Continuous Auto-Polling Correction"; minHeight = 64
            setOnClickListener {
                if (isChecked) requestCalibration(true)
                else stopService(Intent(this@AcousticSettingsActivity, AcousticService::class.java))
            }
        }; box.addView(polling)
        text("Auto-polling repeats the audible 40-second probe every 10 minutes, releases the microphone between checks, and stops in battery saver or below 16% battery. Each follow-up changes a band by at most 0.5 dB. A notification provides Stop. It does not resume after reboot.")
        box.addView(Button(this).apply {
            text = "Stop calibration / auto-polling"
            setOnClickListener {
                stopService(Intent(this@AcousticSettingsActivity, AcousticService::class.java))
                AcousticBus.status = "Stopping calibration / auto-polling."
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

        // v2.1 Sonar Overlay controls
        text("Acoustic Sonar Visualization Overlay").textSize = 20f
        text("Active near-ultrasound sonar mode maps room reflections as dynamic visual artifacts on the existing stress-relief overlay. Uses the same microphone loop; no additional network.")
        box.addView(Switch(this).apply {
            text = "Enable Acoustic Sonar Overlay"; minHeight = 64; isChecked = AcousticBus.state.sonarEnabled
            setOnCheckedChangeListener { _, value -> AcousticBus.sonar(value) }
        })
        text("Sonar Sensitivity / Decay Rate")
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
    }
    private fun requestCalibration(continuous: Boolean) {
        polling.isChecked = AcousticBus.polling
        if (AcousticBus.calibrating || AcousticBus.polling) return
        pendingContinuous = continuous
        AlertDialog.Builder(this).setTitle(if (continuous) "Enable periodic audible calibration?" else "Start 40-second calibration?")
            .setMessage("Use a comfortable media volume and keep the phone still. The microphone measures test tones locally. Existing EQ is retained if measurement fails.")
            .setNegativeButton("Cancel", null).setPositiveButton("Start") { _, _ ->
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
                    requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 40)
                else begin()
            }.show()
    }
    private fun begin() {
        try {
            startForegroundService(Intent(this, AcousticService::class.java).putExtra("continuous", pendingContinuous))
        } catch (_: RuntimeException) {
            AcousticBus.status = "Unable to start microphone service. Open this screen and retry."
        }
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 40 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) begin()
        else AcousticBus.status = "Microphone permission denied. Bell profiles and manual EQ remain available."
    }
    override fun onResume() { super.onResume(); handler.post(refresh) }
    override fun onPause() { handler.removeCallbacks(refresh); super.onPause() }
}
