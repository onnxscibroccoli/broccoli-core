package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.widget.*
import kotlin.math.roundToInt

class SettingsActivity : Activity() {
    private val bands = arrayOf(
        "4.0 Hz - Delta / Deep Theta",
        "6.0 Hz - Theta / Meditative",
        "7.83 Hz - Schumann Resonance",
        "10.0 Hz - Alpha / Relaxed Focus",
        "15.0 Hz - Beta / Alert Cognition",
        "40.0 Hz - Gamma / High Sync"
    )
    private val p by lazy { getSharedPreferences(OverlayService.PREFS, MODE_PRIVATE) }

    private lateinit var hz: Spinner
    private lateinit var mode: RadioGroup
    private lateinit var volume: SeekBar
    private lateinit var fullOpacity: SeekBar
    private lateinit var borderWidth: SeekBar
    private lateinit var borderOpacity: SeekBar
    private lateinit var timedMinutes: EditText
    private lateinit var sunset: Switch
    private lateinit var timed: Switch

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 40, 32, 32)
        }
        val root = ScrollView(this).apply { addView(content) }
        setContentView(root)

        content.addView(TextView(this).apply {
            text = "PARALLAX DISTORTION"
            textSize = 26f
            gravity = Gravity.CENTER
        })
        content.addView(TextView(this).apply {
            text = "Neural Entrainment Engine"
            textSize = 14f
            gravity = Gravity.CENTER
            setPadding(0, 8, 0, 24)
        })

        content.addView(label("Hemi-Sync Target"))
        hz = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@SettingsActivity,
                android.R.layout.simple_spinner_dropdown_item,
                bands
            )
            setSelection(p.getFloat(OverlayService.KEY_HZ, 4f).let { saved ->
                bands.indexOfFirst { it.startsWith(saved.toString()) }.coerceAtLeast(0)
            })
        }
        content.addView(hz)

        content.addView(label("Display Mode"))
        mode = RadioGroup(this).apply {
            orientation = RadioGroup.VERTICAL
            addView(RadioButton(this@SettingsActivity).apply {
                id = 100
                text = "Border Overlay"
                isChecked = !p.getBoolean(OverlayService.KEY_FULL, false)
            })
            addView(RadioButton(this@SettingsActivity).apply {
                id = 101
                text = "Full Screen Overlay"
                isChecked = p.getBoolean(OverlayService.KEY_FULL, false)
            })
        }
        content.addView(mode)

        val seed = EditText(this).apply {
            hint = "Session seed"
            setText(p.getString(OverlayService.KEY_SEED, "PARALLAX_MOBILE"))
        }
        content.addView(seed)

        volume = slider(content, "Volume", 0, 100, (p.getFloat(OverlayService.KEY_VOLUME, .12f) * 100).roundToInt())
        fullOpacity = slider(content, "Full Screen Opacity", 5, 100, (p.getFloat(OverlayService.KEY_FULL_OPACITY, .75f) * 100).roundToInt().coerceIn(5, 100))
        borderWidth = slider(content, "Border Width", 8, 240, p.getFloat(OverlayService.KEY_BORDER_WIDTH, 72f).roundToInt().coerceIn(8, 240))
        borderOpacity = slider(content, "Border Opacity", 0, 100, (p.getFloat(OverlayService.KEY_BORDER_OPACITY, .75f) * 100).roundToInt())

        content.addView(label("Automatic Scheduling"))
        sunset = Switch(this).apply {
            text = "Start automatically at sunset and stop at sunrise"
            isChecked = p.getBoolean(OverlayService.KEY_SUNSET_SUNRISE, false)
        }
        content.addView(sunset)

        timed = Switch(this).apply {
            text = "Use a timed session when Start is pressed"
            isChecked = p.getBoolean(OverlayService.KEY_TIMED, false)
        }
        content.addView(timed)

        timedMinutes = EditText(this).apply {
            hint = "Timed duration (minutes)"
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(p.getInt(OverlayService.KEY_TIMED_MINUTES, 5).toString())
        }
        content.addView(timedMinutes)

        val start = Button(this).apply { text = "Start Session" }
        val stop = Button(this).apply { text = "Stop Session" }
        content.addView(start)
        content.addView(stop)

        sunset.setOnCheckedChangeListener { _, checked ->
            p.edit().putBoolean(OverlayService.KEY_SUNSET_SUNRISE, checked).apply()
            if (checked) requestLocationAndSchedule() else ScheduleReceiver.reschedule(this)
        }
        timed.setOnCheckedChangeListener { _, checked ->
            p.edit().putBoolean(OverlayService.KEY_TIMED, checked).apply()
        }

        start.setOnClickListener {
            if (!Settings.canDrawOverlays(this)) {
                checkOverlayPermission()
                return@setOnClickListener
            }

            val selected = bands[hz.selectedItemPosition].substringBefore(" ").toFloat()
            val minutes = timedMinutes.text.toString().toLongOrNull()?.coerceIn(1, 720) ?: 5L
            val full = mode.checkedRadioButtonId == 101
            val seedText = seed.text.toString().ifBlank { "PARALLAX_MOBILE" }
            val vol = volume.progress / 100f
            val opacity = fullOpacity.progress / 100f
            val bw = borderWidth.progress.toFloat()
            val bo = borderOpacity.progress / 100f

            p.edit()
                .putFloat(OverlayService.KEY_HZ, selected)
                .putBoolean(OverlayService.KEY_FULL, full)
                .putString(OverlayService.KEY_SEED, seedText)
                .putFloat(OverlayService.KEY_VOLUME, vol)
                .putFloat(OverlayService.KEY_FULL_OPACITY, opacity)
                .putFloat(OverlayService.KEY_BORDER_WIDTH, bw)
                .putFloat(OverlayService.KEY_BORDER_OPACITY, bo)
                .putInt(OverlayService.KEY_TIMED_MINUTES, minutes.toInt())
                .apply()

            ScheduleReceiver.reschedule(this)

            val i = Intent(this, OverlayService::class.java).apply {
                putExtra(OverlayService.EXTRA_IS_FULL_OVERLAY, full)
                putExtra(OverlayService.EXTRA_TARGET_HZ, selected)
                putExtra(OverlayService.EXTRA_SEED, seedText)
                putExtra(OverlayService.EXTRA_VOLUME, vol)
                putExtra(OverlayService.EXTRA_FULL_OPACITY, opacity)
                putExtra(OverlayService.EXTRA_BORDER_WIDTH, bw)
                putExtra(OverlayService.EXTRA_BORDER_OPACITY, bo)
                if (timed.isChecked) putExtra(OverlayService.EXTRA_DURATION_MS, minutes * 60_000L)
            }

            if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
        }

        stop.setOnClickListener {
            startService(Intent(this, OverlayService::class.java).apply {
                action = OverlayService.ACTION_STOP
            })
        }

        checkOverlayPermission()
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 2001)
        }
    }

    private fun slider(root: LinearLayout, title: String, min: Int, max: Int, value: Int): SeekBar {
        val text = label(title + "  " + value)
        root.addView(text)
        val bar = SeekBar(this).apply {
            this.max = max - min
            progress = (value - min).coerceIn(0, max - min)
        }
        bar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(s: SeekBar?, v: Int, fromUser: Boolean) {
                text.text = title + "  " + (v + min)
            }
            override fun onStartTrackingTouch(s: SeekBar?) {}
            override fun onStopTrackingTouch(s: SeekBar?) {}
        })
        root.addView(bar)
        return bar
    }

    private fun requestLocationAndSchedule() {
        if (Build.VERSION.SDK_INT >= 23 &&
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION), 3001)
            return
        }
        ScheduleReceiver.reschedule(this)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 3001 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            ScheduleReceiver.reschedule(this)
        }
    }

    private fun label(text: String) = TextView(this).apply {
        this.text = text
        textSize = 12f
        setPadding(0, 12, 0, 4)
    }

    private fun checkOverlayPermission() {
        if (!Settings.canDrawOverlays(this)) {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        }
    }
}
