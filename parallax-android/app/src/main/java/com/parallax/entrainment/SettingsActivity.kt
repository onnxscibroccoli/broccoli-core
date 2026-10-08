package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout.LayoutParams
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
    private lateinit var darkTheme: Switch

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(32))
        }
        val root = ScrollView(this).apply { isFillViewport = true; addView(content) }
        setContentView(root)

        content.addView(TextView(this).apply {
            text = "Parallax Distortion"
            textSize = 28f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            gravity = Gravity.START
            letterSpacing = -.02f
        })
        content.addView(TextView(this).apply {
            text = "Neural Entrainment Engine"
            textSize = 14f
            gravity = Gravity.START
            alpha = .75f
            setPadding(0, dp(4), 0, dp(20))
        })

        darkTheme = Switch(this).apply {
            text = "Dark mode"
            isChecked = p.getBoolean(OverlayService.KEY_DARK_THEME, false)
        }
        content.addView(darkTheme)
        darkTheme.setOnCheckedChangeListener { _, checked ->
            p.edit().putBoolean(OverlayService.KEY_DARK_THEME, checked).apply()
            applySettingsTheme(content, checked)
        }
        applySettingsTheme(content, darkTheme.isChecked)

        content.addView(sectionTitle("Session"))
        content.addView(label("Target frequency"))
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

        content.addView(label("Visual style"))
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

        content.addView(sectionTitle("Appearance & sound"))
        volume = slider(content, "Volume", 0, 100, (p.getFloat(OverlayService.KEY_VOLUME, .12f) * 100).roundToInt(), "%")
        fullOpacity = slider(content, "Full-screen opacity", 5, 100, (p.getFloat(OverlayService.KEY_FULL_OPACITY, .75f) * 100).roundToInt().coerceIn(5, 100), "%")
        borderWidth = slider(content, "Border width", 8, 240, p.getFloat(OverlayService.KEY_BORDER_WIDTH, 72f).roundToInt().coerceIn(8, 240), " dp")
        borderOpacity = slider(content, "Border opacity", 0, 100, (p.getFloat(OverlayService.KEY_BORDER_OPACITY, .75f) * 100).roundToInt(), "%")

        content.addView(sectionTitle("Schedule"))
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
            hint = "Duration in minutes (1–720)"
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(p.getInt(OverlayService.KEY_TIMED_MINUTES, 5).toString())
            singleLine = true
            setPadding(dp(14), dp(12), dp(14), dp(12))
        }
        content.addView(timedMinutes, matchWrap())

        content.addView(sectionTitle("Controls"))
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val start = Button(this).apply { text = "Start session"; isAllCaps = false }
        val stop = Button(this).apply { text = "Stop session"; isAllCaps = false }
        actions.addView(start, LinearLayout.LayoutParams(0, dp(52), 1f).apply { marginEnd = dp(8) })
        actions.addView(stop, LinearLayout.LayoutParams(0, dp(52), 1f))
        content.addView(actions, matchWrap())

        content.addView(sectionTitle("About"))
        val about = TextView(this).apply {
            text = "Created by Ian Cossette with ChatGPT and Gemini\n\nBuy me a coffee ☕️\nCash App: \$icoss\n\nAndroid UI guidance and project source"
            textSize = 14f
            setPadding(dp(16), dp(16), dp(16), dp(16))
            background = rounded(if (darkTheme.isChecked) 0xFF29292C.toInt() else Color.WHITE, 16)
            contentDescription = "About Parallax Distortion. Tap for credits, support, articles and source."
        }
        content.addView(about, matchWrap())
        about.setOnClickListener { showAboutDialog() }

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
            val parsedMinutes = timedMinutes.text.toString().toLongOrNull()
            if (timed.isChecked && (parsedMinutes == null || parsedMinutes !in 1L..720L)) {
                timedMinutes.error = "Enter a duration from 1 to 720 minutes"
                timedMinutes.requestFocus()
                return@setOnClickListener
            }
            val minutes = parsedMinutes?.coerceIn(1, 720) ?: 5L
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

    private fun slider(root: LinearLayout, title: String, min: Int, max: Int, value: Int, suffix: String = ""): SeekBar {
        val text = label(title + "  " + value + suffix)
        root.addView(text)
        val bar = SeekBar(this).apply {
            this.max = max - min
            progress = (value - min).coerceIn(0, max - min)
        }
        bar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(s: SeekBar?, v: Int, fromUser: Boolean) {
                text.text = title + "  " + (v + min) + suffix
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

    private fun applySettingsTheme(root: LinearLayout, dark: Boolean) {
        val bg = if (dark) Color.rgb(27, 27, 28) else Color.rgb(228, 228, 227)
        val fg = if (dark) Color.rgb(228, 228, 227) else Color.rgb(34, 34, 34)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        if (Build.VERSION.SDK_INT >= 23) window.decorView.systemUiVisibility = if (dark) 0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        root.setBackgroundColor(bg)
        fun paint(view: View) {
            if (view is TextView) view.setTextColor(fg)
            if (view is ViewGroup) for (i in 0 until view.childCount) paint(view.getChildAt(i))
        }
        paint(root)
    }

    private fun sectionTitle(title: String) = TextView(this).apply {
        text = title; textSize = 18f; typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        setPadding(0, dp(22), 0, dp(8))
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).roundToInt()
    private fun matchWrap() = LinearLayout.LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)
    private fun rounded(color: Int, radius: Int) = GradientDrawable().apply { setColor(color); cornerRadius = dp(radius).toFloat() }

    private fun showAboutDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(8), dp(20), dp(8)) }
        fun link(title: String, url: String) {
            box.addView(TextView(this).apply {
                text = title; textSize = 15f
                setTextColor(if (darkTheme.isChecked) Color.rgb(160, 190, 235) else Color.rgb(45, 85, 145))
                setPadding(0, dp(10), 0, dp(10))
                setOnClickListener { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
            }, matchWrap())
        }
        box.addView(TextView(this).apply {
            text = "Created by Ian Cossette\nBuilt with ChatGPT and Gemini\n\nSupport development\nBuy me a coffee ☕️\nCash App: \$icoss"
            textSize = 16f; setTextColor(if (darkTheme.isChecked) Color.WHITE else Color.BLACK); setPadding(0, 0, 0, dp(12))
        })
        link("Cash App · \$icoss", "https://cash.app/\$icoss")
        link("Android design: Material 3", "https://m3.material.io/")
        link("Android UI design guidance", "https://developer.android.com/design/ui")
        link("Android accessibility guidance", "https://developer.android.com/guide/topics/ui/accessibility")
        link("Project source · GitHub", "https://github.com/onnxscibroccoli/broccoli-core")
        AlertDialog.Builder(this).setTitle("About Parallax Distortion")
            .setView(ScrollView(this).apply { addView(box) }).setPositiveButton("Done", null).show()
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
