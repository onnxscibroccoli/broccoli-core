package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Handler
import android.os.Looper
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
    private lateinit var audioMode: Spinner
    private lateinit var fullOpacity: SeekBar
    private lateinit var borderWidth: SeekBar
    private lateinit var borderOpacity: SeekBar
    private lateinit var timedMinutes: EditText
    private lateinit var sunset: Switch
    private lateinit var timed: Switch
    private lateinit var darkTheme: Switch
    private lateinit var flashing: Switch
    private var updatingFlashingSwitch = false
    private var showingPermissionGate = false
    private val permissionPromptHandler = Handler(Looper.getMainLooper())
    private val liveUpdateHandler = Handler(Looper.getMainLooper())
    private var pendingLiveUpdate: Runnable? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        OverlayService.migrateVisualDefaults(this)
        if (!hasRequiredPermissions()) {
            showPermissionsScreen()
            return
        }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(32))
        }
        val root = ScrollView(this).apply { isFillViewport = true; addView(content) }
        val appFrame = FrameLayout(this).apply {
            addView(root, FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT
            ))
        }
        setContentView(appFrame)
        val splash = EntrainmentSurfaceView(
            this, true, 4f, "PARALLAX_SETTINGS_SPLASH",
            1f, 72f, 1f, false
        ).apply {
            contentDescription = "Parallax Distortion animated splash"
            alpha = 1f
        }
        appFrame.addView(splash, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT
        ))
        splash.animate().alpha(0f).setStartDelay(0L).setDuration(1500L).withEndAction {
            appFrame.removeView(splash)
        }.start()

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val heading = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        heading.addView(TextView(this).apply {
            text = "Parallax Distortion"
            textSize = 28f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            gravity = Gravity.START
            letterSpacing = -.02f
        })
        heading.addView(TextView(this).apply {
            text = "Neural Entrainment Engine"
            textSize = 14f
            gravity = Gravity.START
            alpha = .75f
            setPadding(0, dp(4), 0, dp(12))
        })
        header.addView(heading, LinearLayout.LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
        val menuButton = Button(this).apply {
            text = "☰"
            textSize = 24f
            minWidth = dp(52)
            minHeight = dp(52)
            contentDescription = "Open navigation menu"
            isAllCaps = false
        }
        header.addView(menuButton)
        content.addView(header, matchWrap())
        menuButton.setOnClickListener { anchor ->
            PopupMenu(this, anchor).apply {
                menu.add(0, 1, 0, "Permissions & access")
                menu.add(0, 2, 1, "Audio controls")
                menu.add(0, 3, 2, "About Parallax Distortion")
                setOnMenuItemClickListener { item ->
                    when (item.itemId) {
                        1 -> showPermissionManagement()
                        2 -> showAudioHelp()
                        3 -> showAboutDialog()
                    }
                    true
                }
            }.show()
        }

        darkTheme = Switch(this).apply {
            text = "Dark mode"
            minHeight = dp(52)
            isChecked = p.getBoolean(OverlayService.KEY_DARK_THEME, true)
        }
        content.addView(darkTheme)
        darkTheme.setOnCheckedChangeListener { _, checked ->
            p.edit().putBoolean(OverlayService.KEY_DARK_THEME, checked).apply()
            applySettingsTheme(content, checked)
            requestLiveUpdate()
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
        hz.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                p.edit().putFloat(OverlayService.KEY_HZ, bands[position].substringBefore(" ").toFloat()).apply()
                requestLiveUpdate()
            }
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        }

        content.addView(label("Visual style"))
        mode = RadioGroup(this).apply {
            orientation = RadioGroup.VERTICAL
            addView(RadioButton(this@SettingsActivity).apply {
                id = 100
                minHeight = dp(48)
                text = "Border overlay"
                isChecked = !p.getBoolean(OverlayService.KEY_FULL, false)
            })
            addView(RadioButton(this@SettingsActivity).apply {
                id = 101
                minHeight = dp(48)
                text = "Full-screen overlay"
                isChecked = p.getBoolean(OverlayService.KEY_FULL, false)
            })
        }
        content.addView(mode)
        mode.setOnCheckedChangeListener { _, checkedId ->
            p.edit().putBoolean(OverlayService.KEY_FULL, checkedId == 101).apply()
            requestLiveUpdate()
        }

        content.addView(sectionTitle("Visual safety"))
        flashing = Switch(this).apply {
            text = "Enable rhythmic flashing"
            isChecked = p.getBoolean(OverlayService.KEY_FLASHING, false)
            minHeight = dp(52)
            contentDescription = "Enable or disable rhythmic visual pulsing. Disabled by default."
        }
        content.addView(flashing, matchWrap())
        content.addView(TextView(this).apply {
            text = "Flashing effects can trigger seizures or other symptoms in people with photosensitive epilepsy. Keep this off if you are sensitive to flashing lights."
            textSize = 13f
            alpha = .82f
            setPadding(0, dp(4), 0, dp(8))
        }, matchWrap())
        flashing.setOnCheckedChangeListener { button, checked ->
            if (updatingFlashingSwitch) return@setOnCheckedChangeListener
            if (checked) {
                // Never enable flashing until the user explicitly acknowledges the safety warning.
                updatingFlashingSwitch = true
                button.isChecked = false
                updatingFlashingSwitch = false
                AlertDialog.Builder(this)
                    .setTitle("Photosensitivity warning")
                    .setMessage("Rhythmic flashing or pulsing visuals may trigger seizures, dizziness, migraine, or other symptoms, especially for people with photosensitive epilepsy. Do not proceed if you have a history of photosensitive seizures or are unsure whether flashing effects are safe for you. Stop immediately if you feel unwell.\n\nFlashing is disabled by default.")
                    .setPositiveButton("Proceed") { _, _ ->
                        p.edit().putBoolean(OverlayService.KEY_FLASHING, true).apply()
                        requestLiveUpdate()
                        updatingFlashingSwitch = true
                        button.isChecked = true
                        updatingFlashingSwitch = false
                    }
                    .setNegativeButton("Cancel") { _, _ ->
                        p.edit().putBoolean(OverlayService.KEY_FLASHING, false).apply()
                        requestLiveUpdate()
                        updatingFlashingSwitch = true
                        button.isChecked = false
                        updatingFlashingSwitch = false
                    }
                    .setOnCancelListener {
                        p.edit().putBoolean(OverlayService.KEY_FLASHING, false).apply()
                        requestLiveUpdate()
                        updatingFlashingSwitch = true
                        button.isChecked = false
                        updatingFlashingSwitch = false
                    }
                    .show()
            } else {
                p.edit().putBoolean(OverlayService.KEY_FLASHING, false).apply()
                requestLiveUpdate()
            }
        }

        val seed = EditText(this).apply {
            hint = "Session seed (optional)"
            minHeight = dp(52)
            setPadding(dp(14), dp(12), dp(14), dp(12))
            setText(p.getString(OverlayService.KEY_SEED, "PARALLAX_MOBILE"))
        }
        content.addView(seed)
        seed.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                p.edit().putString(OverlayService.KEY_SEED, s?.toString().orEmpty().ifBlank { "PARALLAX_MOBILE" }).apply()
                requestLiveUpdate()
            }
            override fun afterTextChanged(s: android.text.Editable?) {}
        })

        content.addView(sectionTitle("Audio"))
        content.addView(label("Audio behavior"))
        audioMode = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@SettingsActivity,
                android.R.layout.simple_spinner_item,
                arrayOf("Audio off", "Play alongside other apps", "Duck other apps")
            ).also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
            setSelection(p.getInt(OverlayService.KEY_AUDIO_MODE, OverlayService.AUDIO_MODE_MIX).coerceIn(0, 2))
            contentDescription = "Audio behavior"
        }
        content.addView(audioMode, matchWrap())
        content.addView(TextView(this).apply {
            text = "Off is silent. Alongside keeps other apps at their current volume. Duck asks compatible apps to lower their audio while Parallax plays."
            textSize = 13f
            alpha = .78f
            setPadding(0, dp(4), 0, dp(8))
        }, matchWrap())
        audioMode.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                p.edit().putInt(OverlayService.KEY_AUDIO_MODE, position).apply()
                requestLiveUpdate()
            }
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        }

        content.addView(sectionTitle("Appearance"))
        volume = slider(content, "Volume", 0, 100, (p.getFloat(OverlayService.KEY_VOLUME, .12f) * 100).roundToInt(), "%") {
            p.edit().putFloat(OverlayService.KEY_VOLUME, it / 100f).apply()
            requestLiveUpdate()
        }
        fullOpacity = slider(content, "Full-screen opacity", 5, 100, (p.getFloat(OverlayService.KEY_FULL_OPACITY, .33f) * 100).roundToInt().coerceIn(5, 100), "%") {
            p.edit().putFloat(OverlayService.KEY_FULL_OPACITY, it / 100f).apply()
            requestLiveUpdate()
        }
        borderWidth = slider(content, "Border width", 8, 240, p.getFloat(OverlayService.KEY_BORDER_WIDTH, 72f).roundToInt().coerceIn(8, 240), " dp") {
            p.edit().putFloat(OverlayService.KEY_BORDER_WIDTH, it.toFloat()).apply()
            requestLiveUpdate()
        }
        borderOpacity = slider(content, "Border opacity", 0, 100, (p.getFloat(OverlayService.KEY_BORDER_OPACITY, .33f) * 100).roundToInt(), "%") {
            p.edit().putFloat(OverlayService.KEY_BORDER_OPACITY, it / 100f).apply()
            requestLiveUpdate()
        }

        content.addView(sectionTitle("Schedule"))
        sunset = Switch(this).apply {
            minHeight = dp(52)
            text = "Start automatically at sunset and stop at sunrise"
            isChecked = p.getBoolean(OverlayService.KEY_SUNSET_SUNRISE, false)
        }
        content.addView(sunset)

        timed = Switch(this).apply {
            minHeight = dp(52)
            text = "Use a timed session when Start is pressed"
            isChecked = p.getBoolean(OverlayService.KEY_TIMED, false)
        }
        content.addView(timed)

        timedMinutes = EditText(this).apply {
            hint = "Duration in minutes (1–720)"
            inputType = InputType.TYPE_CLASS_NUMBER
            minHeight = dp(52)
            setText(p.getInt(OverlayService.KEY_TIMED_MINUTES, 5).toString())
            setSingleLine(true)
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

        sunset.setOnCheckedChangeListener { _, checked ->
            p.edit().putBoolean(OverlayService.KEY_SUNSET_SUNRISE, checked).apply()
            if (checked) requestLocationAndSchedule() else ScheduleReceiver.reschedule(this)
        }
        timed.setOnCheckedChangeListener { _, checked ->
            p.edit().putBoolean(OverlayService.KEY_TIMED, checked).apply()
        }
        timedMinutes.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                s?.toString()?.toIntOrNull()?.takeIf { it in 1..720 }?.let {
                    p.edit().putInt(OverlayService.KEY_TIMED_MINUTES, it).apply()
                }
            }
            override fun afterTextChanged(s: android.text.Editable?) {}
        })

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

    }

    override fun onResume() {
        super.onResume()
        if (hasRequiredPermissions()) {
            if (showingPermissionGate) {
                showingPermissionGate = false
                recreate()
            }
        } else {
            showPermissionsScreen()
        }
    }

    private fun requestLiveUpdate() {
        pendingLiveUpdate?.let { liveUpdateHandler.removeCallbacks(it) }
        val updateTask = Runnable {
            if (p.getBoolean(OverlayService.KEY_SESSION_ACTIVE, false)) {
                val update = Intent(this, OverlayService::class.java).apply { action = OverlayService.ACTION_UPDATE }
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(update) else startService(update)
            }
        }
        pendingLiveUpdate = updateTask
        liveUpdateHandler.postDelayed(updateTask, 90L)
    }

    override fun onDestroy() {
        permissionPromptHandler.removeCallbacksAndMessages(null)
        liveUpdateHandler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private fun slider(
        root: LinearLayout, title: String, min: Int, max: Int, value: Int,
        suffix: String = "", onChanged: ((Int) -> Unit)? = null
    ): SeekBar {
        val text = label(title + "  " + value + suffix)
        root.addView(text)
        val bar = SeekBar(this).apply {
            minHeight = dp(48)
            contentDescription = title
            this.max = max - min
            progress = (value - min).coerceIn(0, max - min)
        }
        bar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(s: SeekBar?, v: Int, fromUser: Boolean) {
                text.text = title + "  " + (v + min) + suffix
                if (fromUser) onChanged?.invoke(v + min)
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
        if (requestCode == 2001 && showingPermissionGate && hasRequiredPermissions()) {
            showingPermissionGate = false
            recreate()
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
        text = title.uppercase()
        textSize = 12f
        letterSpacing = .12f
        alpha = .82f
        typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        setPadding(0, dp(26), 0, dp(8))
        accessibilityHeading = true
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).roundToInt()
    private fun matchWrap() = LinearLayout.LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)
    private fun rounded(color: Int, radius: Int) = GradientDrawable().apply { setColor(color); cornerRadius = dp(radius).toFloat() }

    private fun hasRequiredPermissions(): Boolean =
        Settings.canDrawOverlays(this) &&
            (Build.VERSION.SDK_INT < 33 ||
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED)

    private fun isNotificationPermissionGranted(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun showPermissionsScreen() {
        showingPermissionGate = true
        val dark = p.getBoolean(OverlayService.KEY_DARK_THEME, true)
        val bg = if (dark) Color.rgb(27, 27, 28) else Color.rgb(244, 244, 242)
        val fg = if (dark) Color.rgb(238, 238, 238) else Color.rgb(34, 34, 34)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        if (Build.VERSION.SDK_INT >= 23) window.decorView.systemUiVisibility =
            if (dark) 0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(32), dp(24), dp(32))
            setBackgroundColor(bg)
        }
        val scroll = ScrollView(this).apply { isFillViewport = true; addView(content) }
        setContentView(scroll)
        content.addView(TextView(this).apply {
            text = "Welcome to Parallax Distortion"
            textSize = 28f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            setTextColor(fg)
        })
        content.addView(TextView(this).apply {
            text = "A couple of Android permissions are needed before the visual overlay can run. You can review each permission below and return here to continue."
            textSize = 15f
            setTextColor(fg)
            alpha = .85f
            setPadding(0, dp(10), 0, dp(22))
        })
        val overlayGranted = Settings.canDrawOverlays(this)
        permissionRow(content, "Display over other apps", "Required to render the overlay above other apps.", overlayGranted, fg)
        val overlayButton = Button(this).apply {
            text = if (overlayGranted) "Overlay access granted" else "Grant overlay access"
            isEnabled = !overlayGranted
            isAllCaps = false
            minHeight = dp(52)
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
            }
        }
        content.addView(overlayButton, matchWrap())

        val notificationsGranted = isNotificationPermissionGranted()
        permissionRow(content, "Notifications", if (Build.VERSION.SDK_INT >= 33)
            "Allows Android to show session status and foreground-service notifications."
            else "Handled by Android on this version.", notificationsGranted, fg)
        val notificationButton = Button(this).apply {
            text = if (notificationsGranted) "Notifications allowed" else "Allow notifications"
            isEnabled = !notificationsGranted
            isAllCaps = false
            minHeight = dp(52)
            setOnClickListener {
                if (Build.VERSION.SDK_INT >= 33) {
                    requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 2001)
                }
            }
        }
        content.addView(notificationButton, matchWrap())
        content.addView(TextView(this).apply {
            text = "Permissions are checked again whenever you return from Android Settings. If you change your mind later, open the menu and choose Permissions & access."
            textSize = 13f
            setTextColor(fg)
            alpha = .75f
            setPadding(0, dp(20), 0, dp(12))
        })
        content.addView(Button(this).apply {
            text = if (hasRequiredPermissions()) "Continue" else "Check permissions again"
            isAllCaps = false
            minHeight = dp(54)
            setOnClickListener {
                if (hasRequiredPermissions()) {
                    showingPermissionGate = false
                    recreate()
                } else {
                    showPermissionsScreen()
                    if (!Settings.canDrawOverlays(this@SettingsActivity)) {
                        Toast.makeText(this@SettingsActivity, "Overlay access is still required.", Toast.LENGTH_SHORT).show()
                    } else if (!isNotificationPermissionGranted()) {
                        Toast.makeText(this@SettingsActivity, "Please allow notifications to continue.", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }, matchWrap())

        if (!p.getBoolean(OverlayService.KEY_PERMISSION_PROMPT_SHOWN, false)) {
            permissionPromptHandler.removeCallbacksAndMessages(null)
            permissionPromptHandler.postDelayed({
                if (!isFinishing && showingPermissionGate && !hasRequiredPermissions() &&
                    !p.getBoolean(OverlayService.KEY_PERMISSION_PROMPT_SHOWN, false)
                ) {
                    p.edit().putBoolean(OverlayService.KEY_PERMISSION_PROMPT_SHOWN, true).apply()
                    AlertDialog.Builder(this)
                        .setTitle("Permissions needed")
                        .setMessage(
                            "Parallax Distortion needs these permissions to function:\n" +
                            "• Display over other apps, to show the visual overlay\n" +
                            "• Notifications, to show session status\n\n" +
                            "No data ever leaves your device.\n\n" +
                            "The source code is available on GitHub."
                        )
                        .setNeutralButton("View source") { _, _ ->
                            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/onnxscibroccoli/broccoli-core")))
                        }
                        .setPositiveButton("Grant permissions") { _, _ ->
                            if (!Settings.canDrawOverlays(this)) {
                                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
                            } else if (!isNotificationPermissionGranted() && Build.VERSION.SDK_INT >= 33) {
                                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 2001)
                            }
                        }
                        .setNegativeButton("Cancel", null)
                        .show()
                }
            }, 4000L)
        }
    }

    private fun permissionRow(root: LinearLayout, title: String, detail: String, granted: Boolean, fg: Int) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = rounded(if (p.getBoolean(OverlayService.KEY_DARK_THEME, true))
                Color.rgb(43, 43, 46) else Color.WHITE, 14)
        }
        card.addView(TextView(this).apply {
            text = title + if (granted) "  ✓ Granted" else "  • Required"
            textSize = 16f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            setTextColor(fg)
        })
        card.addView(TextView(this).apply {
            text = detail
            textSize = 13f
            setTextColor(fg)
            alpha = .8f
            setPadding(0, dp(5), 0, 0)
        })
        root.addView(card, matchWrap())
        root.addView(Space(this), LinearLayout.LayoutParams(1, dp(10)))
    }

    private fun showPermissionManagement() {
        val dark = p.getBoolean(OverlayService.KEY_DARK_THEME, true)
        val fg = if (dark) Color.WHITE else Color.rgb(34, 34, 34)
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(8))
        }
        fun status(title: String, detail: String, granted: Boolean, actionLabel: String, action: () -> Unit) {
            box.addView(TextView(this).apply {
                text = title + if (granted) "  ✓ Granted" else "  • Needed"
                textSize = 16f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                setTextColor(fg)
                setPadding(0, dp(10), 0, dp(3))
            })
            box.addView(TextView(this).apply {
                text = detail
                textSize = 13f
                setTextColor(fg)
                alpha = .8f
            })
            box.addView(Button(this).apply {
                text = actionLabel
                isAllCaps = false
                minHeight = dp(48)
                isEnabled = !granted
                setOnClickListener { action() }
            }, matchWrap())
        }
        val overlay = Settings.canDrawOverlays(this)
        status("Display over other apps", "Required for the visual overlay.", overlay,
            if (overlay) "Granted" else "Open overlay settings") {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        }
        val notifications = isNotificationPermissionGranted()
        status("Notifications", "Used for session and foreground-service status.", notifications,
            if (notifications) "Granted" else "Request notification permission") {
            if (Build.VERSION.SDK_INT >= 33) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 2001)
        }
        val location = checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        status("Location for sunset scheduling", "Optional. Only needed when enabling sunset-to-sunrise scheduling.", location,
            if (location) "Granted" else "Allow location") {
            if (Build.VERSION.SDK_INT >= 23) requestPermissions(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION), 3001)
        }
        AlertDialog.Builder(this)
            .setTitle("Permissions & access")
            .setView(ScrollView(this).apply { addView(box) })
            .setPositiveButton("Done", null)
            .show()
    }

    private fun showAudioHelp() {
        val dark = p.getBoolean(OverlayService.KEY_DARK_THEME, true)
        val fg = if (dark) Color.rgb(242, 242, 242) else Color.rgb(32, 32, 32)
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(8))
        }
        val rows = listOf(
            "Audio off" to "Stops Parallax audio output. Visual effects continue normally.",
            "Play alongside other apps" to "Default. Parallax audio continues without requesting audio focus, so other apps can keep playing at their existing volume.",
            "Duck other apps" to "Requests transient audio focus with ducking. Apps that honor Android audio focus lower their volume while Parallax plays; some apps may pause or ignore ducking."
        )
        rows.forEach { (title, detail) ->
            box.addView(TextView(this).apply {
                text = title
                textSize = 16f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                setTextColor(fg)
                setPadding(0, dp(12), 0, dp(4))
            })
            box.addView(TextView(this).apply {
                text = detail
                textSize = 14f
                setTextColor(fg)
                setLineSpacing(dp(2).toFloat(), 1f)
            })
        }
        AlertDialog.Builder(this)
            .setTitle("Audio controls")
            .setView(ScrollView(this).apply { addView(box) })
            .setPositiveButton("Done", null)
            .show()
    }

    private fun showAboutDialog() {
        val dark = p.getBoolean(OverlayService.KEY_DARK_THEME, true)
        val fg = if (dark) Color.rgb(242, 242, 242) else Color.rgb(32, 32, 32)
        val muted = if (dark) Color.rgb(190, 190, 196) else Color.rgb(86, 86, 92)
        val accent = if (dark) Color.rgb(164, 194, 245) else Color.rgb(42, 83, 145)
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(12))
        }
        fun heading(title: String) {
            box.addView(TextView(this).apply {
                text = title.uppercase()
                textSize = 12f
                letterSpacing = .08f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                setTextColor(muted)
                setPadding(0, dp(18), 0, dp(6))
            })
        }
        fun paragraph(text: String) {
            box.addView(TextView(this).apply {
                this.text = text
                textSize = 14f
                setTextColor(fg)
                setLineSpacing(dp(3).toFloat(), 1f)
            })
        }
        fun link(title: String, url: String) {
            box.addView(TextView(this).apply {
                text = title + "  ↗"
                textSize = 15f
                setTextColor(accent)
                isFocusable = true
                minHeight = dp(44)
                gravity = Gravity.CENTER_VERTICAL
                setOnClickListener {
                    try {
                        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    } catch (_: Exception) {
                        Toast.makeText(this@SettingsActivity, "No app available to open this link.", Toast.LENGTH_SHORT).show()
                    }
                }
            }, matchWrap())
        }
        val hero = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = rounded(if (dark) Color.rgb(43, 43, 47) else Color.WHITE, 18)
        }
        hero.addView(TextView(this).apply {
            text = "Parallax Distortion"
            textSize = 24f
            typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
            setTextColor(fg)
        })
        hero.addView(TextView(this).apply {
            text = "Ambient visuals and audio  ·  Version 1.9.0"
            textSize = 13f
            setTextColor(muted)
            setPadding(0, dp(5), 0, 0)
        })
        hero.addView(TextView(this).apply {
            text = "A customizable ambient visual overlay with session timing, refined appearance controls, and optional audio behavior settings."
            textSize = 14f
            setTextColor(fg)
            setPadding(0, dp(14), 0, 0)
        })
        box.addView(hero, matchWrap())
        heading("Designed with care")
        paragraph("Built by Ian Cossette with assistance from ChatGPT and Gemini. The app is designed around adjustable visual styles, clear controls, and explicit consent for rhythmic flashing.")
        heading("Safety & control")
        paragraph("Rhythmic flashing is off by default and requires confirmation before it can be enabled. Stop using the effect immediately if it causes discomfort. This app is not a medical device and does not provide medical treatment.")
        heading("Permissions & privacy")
        paragraph("Overlay access enables the visual layer. Notifications support visible session status. Location is optional and is only requested for sunset-to-sunrise scheduling. Permissions can be reviewed at any time from the navigation menu.")
        heading("Support development")
        paragraph("If you find the app useful, you can support continued development.")
        link("Cash App · \$icoss", "https://cash.app/\$icoss")
        heading("Resources")
        link("Project source · GitHub", "https://github.com/onnxscibroccoli/broccoli-core")
        link("Android design system · Material 3", "https://m3.material.io/")
        link("Android UI design guidance", "https://developer.android.com/design/ui")
        link("Android accessibility guidance", "https://developer.android.com/guide/topics/ui/accessibility")
        AlertDialog.Builder(this)
            .setTitle("About")
            .setView(ScrollView(this).apply { addView(box) })
            .setPositiveButton("Done", null)
            .show()
    }

    private fun label(text: String) = TextView(this).apply {
        this.text = text
        textSize = 14f
        setPadding(0, dp(12), 0, dp(4))
    }

    private fun checkOverlayPermission() {
        if (!Settings.canDrawOverlays(this)) {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        }
    }
}
