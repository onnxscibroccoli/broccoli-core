package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.widget.*

class SettingsActivity : Activity() {
    private lateinit var hz: Spinner
    private lateinit var mode: RadioGroup
    private val bands = arrayOf(
        "4.0 Hz - Delta / Deep Theta",
        "6.0 Hz - Theta / Meditative",
        "7.83 Hz - Schumann Resonance",
        "10.0 Hz - Alpha / Relaxed Focus",
        "15.0 Hz - Beta / Alert Cognition",
        "40.0 Hz - Gamma / High Sync"
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 40, 32, 32)
        }

        root.addView(TextView(this).apply {
            text = "PARALLAX DISTORTION"
            textSize = 26f
            gravity = Gravity.CENTER
        })
        root.addView(TextView(this).apply {
            text = "Neural Entrainment Engine"
            textSize = 14f
            gravity = Gravity.CENTER
            setPadding(0, 8, 0, 32)
        })

        hz = Spinner(this).apply {
            adapter = ArrayAdapter(this@SettingsActivity, android.R.layout.simple_spinner_dropdown_item, bands)
        }
        root.addView(hz)

        mode = RadioGroup(this).apply {
            orientation = RadioGroup.VERTICAL
            addView(RadioButton(this@SettingsActivity).apply { id = 100; text = "Border Overlay"; isChecked = true })
            addView(RadioButton(this@SettingsActivity).apply { id = 101; text = "Full Screen Overlay" })
        }
        root.addView(mode)

        val seed = EditText(this).apply {
            hint = "Session seed"
            setText("PARALLAX_MOBILE")
        }
        root.addView(seed)

        val start = Button(this).apply { text = "Start Session" }
        val stop = Button(this).apply { text = "Stop Session" }
        root.addView(start)
        root.addView(stop)
        setContentView(root)

        checkOverlayPermission()

        start.setOnClickListener {
            if (!Settings.canDrawOverlays(this)) {
                checkOverlayPermission()
                return@setOnClickListener
            }
            val selected = bands[hz.selectedItemPosition].substringBefore(" ").toFloat()
            val intent = Intent(this, OverlayService::class.java).apply {
                putExtra(OverlayService.EXTRA_IS_FULL_OVERLAY, mode.checkedRadioButtonId == 101)
                putExtra(OverlayService.EXTRA_TARGET_HZ, selected)
                putExtra(OverlayService.EXTRA_SEED, seed.text.toString().ifBlank { "PARALLAX_MOBILE" })
            }
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
        }

        stop.setOnClickListener {
            startService(Intent(this, OverlayService::class.java).apply { action = OverlayService.ACTION_STOP })
        }

        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 2001)
        }
    }

    private fun checkOverlayPermission() {
        if (!Settings.canDrawOverlays(this)) {
            startActivity(Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            ))
        }
    }
}
