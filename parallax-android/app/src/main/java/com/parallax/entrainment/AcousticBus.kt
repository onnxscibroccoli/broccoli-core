package com.parallax.entrainment

import android.content.Context
import android.content.SharedPreferences

/** Immutable state events shared by UI, calibration worker and the audio worker. */
data class AcousticState(
    val auto: List<Float> = List(7) { 0f },
    val manual: List<Float> = List(7) { 0f },
    val locked: List<Boolean> = List(7) { false },
    val bells: Boolean = false,
    val profile: Int = 4,
    val bellCarrier: Boolean = true,
    val bowlMode: Boolean = false,
    val bellRingSeconds: Int = 16,
    val bellIntervalSeconds: Int = 24,
    val hourlyChime: Boolean = false,
    val sonarEnabled: Boolean = false,
    val sonarSensitivity: Float = 0.5f,
    val sonarLevels: List<Float> = List(7) { 0f },
    val sonarMeasured: Boolean = false
) {
    val effective = AcousticDsp.effective(auto, manual, locked)
}

object AcousticBus {
    @Volatile var state = AcousticState(); private set
    @Volatile var calibrating = false
    @Volatile var polling = false
    @Volatile var status = "Ready. Calibration uses the built-in speaker and microphone."
    private var prefs: SharedPreferences? = null
    @Synchronized fun initialize(context: Context) {
        if (prefs != null) return
        val p = context.applicationContext.getSharedPreferences("acoustic_v2", Context.MODE_PRIVATE)
        prefs = p
        state = AcousticState(
            auto = List(7) { p.getFloat("auto_$it", 0f).takeIf { it.isFinite() }?.coerceIn(-6f, 0f) ?: 0f },
            manual = List(7) { p.getFloat("manual_$it", 0f).takeIf { it.isFinite() }?.coerceIn(-12f, 6f) ?: 0f },
            locked = List(7) { p.getBoolean("locked_$it", false) },
            bells = p.getBoolean("bells", false), profile = p.getInt("profile", 4).coerceIn(0, 8),
            bellCarrier = p.getBoolean("bell_carrier", true),
            bowlMode = p.getBoolean("bowl_mode", false),
            bellRingSeconds = p.getInt("bell_ring_seconds", 16).coerceIn(2, 60),
            bellIntervalSeconds = p.getInt("bell_interval_seconds", 24).coerceIn(4, 300),
            hourlyChime = p.getBoolean("hourly_chime", false),
            sonarEnabled = p.getBoolean("sonar_enabled", false),
            sonarSensitivity = p.getFloat("sonar_sensitivity", 0.5f).takeIf { it.isFinite() }?.coerceIn(0f, 1f) ?: 0.5f,
            sonarLevels = List(7) { p.getFloat("sonar_band_$it", 0f).takeIf { v -> v.isFinite() }?.coerceIn(0f, 1f) ?: 0f },
            sonarMeasured = p.getBoolean("sonar_measured", false)
        )
    }
    @Synchronized private fun publish(next: AcousticState) {
        state = next
        prefs?.edit()?.apply {
            for (i in 0..6) {
                putFloat("auto_$i", next.auto[i]); putFloat("manual_$i", next.manual[i]); putBoolean("locked_$i", next.locked[i])
            }
            putBoolean("bells", next.bells); putInt("profile", next.profile)
            putBoolean("bell_carrier", next.bellCarrier); putBoolean("bowl_mode", next.bowlMode)
            putInt("bell_ring_seconds", next.bellRingSeconds)
            putInt("bell_interval_seconds", next.bellIntervalSeconds)
            putBoolean("hourly_chime", next.hourlyChime)
            putBoolean("sonar_enabled", next.sonarEnabled); putFloat("sonar_sensitivity", next.sonarSensitivity)
            for (i in 0..6) putFloat("sonar_band_$i", next.sonarLevels[i])
            putBoolean("sonar_measured", next.sonarMeasured)
        }?.apply()
    }
    @Synchronized fun manual(band: Int, db: Float) {
        publish(state.copy(manual = state.manual.mapIndexed { i, old -> if (i == band) db.coerceIn(-12f, 6f) else old },
            locked = state.locked.mapIndexed { i, old -> i == band || old }))
    }
    @Synchronized fun resetManual() = publish(state.copy(locked = List(7) { false }))
    @Synchronized fun bells(enabled: Boolean) = publish(state.copy(bells = enabled))
    @Synchronized fun profile(index: Int) = publish(state.copy(profile = index.coerceIn(0, 8)))
    @Synchronized fun bellCarrier(value: Boolean) = publish(state.copy(bellCarrier = value))
    @Synchronized fun bowlMode(value: Boolean) = publish(state.copy(bowlMode = value))
    @Synchronized fun bellRingSeconds(value: Int) = publish(state.copy(bellRingSeconds = value.coerceIn(2, 60)))
    @Synchronized fun bellIntervalSeconds(value: Int) = publish(state.copy(bellIntervalSeconds = value.coerceIn(4, 300)))
    @Synchronized fun hourlyChime(value: Boolean) = publish(state.copy(hourlyChime = value))
    @Synchronized fun correction(value: List<Float>, micro: Boolean) {
        publish(state.copy(auto = if (micro) AcousticDsp.microCorrection(state.auto, value) else value.toList()))
    }
    @Synchronized fun sonar(enabled: Boolean) = publish(state.copy(sonarEnabled = enabled))
    @Synchronized fun sonarSensitivity(value: Float) =
        if (value.isFinite()) publish(state.copy(sonarSensitivity = value.coerceIn(0f, 1f))) else Unit

    /** Derived seven-band spectral shape only. Never store microphone PCM. */
    @Synchronized fun sonarReading(levels: List<Float>) {
        if (levels.size != 7 || levels.any { !it.isFinite() || it !in 0f..1f }) return
        publish(state.copy(sonarLevels = levels.toList(), sonarMeasured = true))
    }
}
