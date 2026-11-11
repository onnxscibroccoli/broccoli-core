package com.parallax.entrainment

import kotlin.math.*

/** Pure DSP: no permissions, Android objects, persistence, or allocations per sample. */
object AcousticDsp {
    val bands = listOf(125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0)
    val bells = listOf(174.0, 285.0, 396.0, 417.0, 528.0, 639.0, 741.0, 852.0, 963.0)
    fun effective(auto: List<Float>, manual: List<Float>, locked: List<Boolean>): List<Float> =
        bands.indices.map { (if (locked[it]) manual[it] else auto[it]).let { v ->
            if (v.isFinite()) v.coerceIn(-12f, 6f) else 0f
        } }

    // Windowed complex projection. Averaging powers avoids phase cancellation.
    fun power(samples: ShortArray, count: Int, hz: Double, rate: Int): Double {
        require(count in 2..samples.size)
        var re = 0.0; var im = 0.0; var weight = 0.0
        for (i in 0 until count) {
            val w = 0.5 - 0.5 * cos(2 * PI * i / (count - 1))
            val x = samples[i] / 32768.0 * w
            val phase = 2 * PI * hz * i / rate
            re += x * cos(phase); im += x * sin(phase); weight += w
        }
        return 4 * (re * re + im * im) / (weight * weight)
    }

    /** Reject the entire run if any band is below 10 dB SNR; never boost nulls. */
    fun correction(noise: List<Double>, measured: List<Double>): List<Float>? {
        require(noise.size == bands.size && measured.size == bands.size)
        if (bands.indices.any { !noise[it].isFinite() || !measured[it].isFinite() ||
                noise[it] < 0 || measured[it] < 1e-9 || measured[it] < max(noise[it], 1e-12) * 10 }) return null
        val db = measured.mapIndexed { i, v -> 10 * log10(max(v - noise[i], 1e-12)) }
        val median = db.sorted()[db.size / 2]
        return db.map { (median - it).coerceIn(-6.0, 0.0).toFloat() }
    }


    data class AdaptiveResult(
        /** Null means the band was unreliable; retain the previous correction. */
        val bands: List<Float?>,
        val validCount: Int,
        val weakHz: List<Int>
    )

    /** Accept only measured bands with useful SNR; do not extrapolate into nulls. */
    fun adaptiveCorrection(noise: List<Double>, signal: List<Double>): AdaptiveResult? {
        if (noise.size != bands.size || signal.size != bands.size) return null
        val valid = bands.indices.filter { i ->
            val n = noise[i]; val s = signal[i]
            n.isFinite() && s.isFinite() && n >= 0 && s > 1e-9 &&
                s > max(n, 1e-12) * 4.0
        }
        // At least four independent bands required for a meaningful median.
        if (valid.size < 4) return null
        val db = valid.map { i ->
            10 * log10(max(signal[i] - noise[i], 1e-12))
        }.sorted()
        val median = db[db.size / 2]
        val values = bands.indices.map { i ->
            if (i !in valid) null
            else (median - 10 * log10(max(signal[i] - noise[i], 1e-12)))
                .coerceIn(-6.0, 0.0).toFloat()
        }
        return AdaptiveResult(values, valid.size,
            bands.indices.filter { it !in valid }.map { bands[it].toInt() })
    }

    fun microCorrection(old: List<Float>, target: List<Float>) = old.indices.map {
        (old[it] + (target[it] - old[it]).coerceIn(-0.5f, 0.5f)).coerceIn(-6f, 0f)
    }
    /** Relative spectral levels from a successful calibration, not range or echo timing. */
    fun normalizedSpectrum(noise: List<Double>, measured: List<Double>): List<Float>? {
        if (noise.size != bands.size || measured.size != bands.size) return null
        if (bands.indices.any { !noise[it].isFinite() || !measured[it].isFinite() ||
                noise[it] < 0.0 || measured[it] <= noise[it] }) return null
        val db = bands.indices.map { 10.0 * log10(max(measured[it] - noise[it], 1e-12)) }
        val peak = db.maxOrNull() ?: return null
        return db.map { ((it - (peak - 36.0)) / 36.0).coerceIn(0.0, 1.0).toFloat() }
    }
}

/** Independent stereo modal voices support a true interaural frequency difference. */
class BellSynth(private val rate: Int) {
    private val bellRatios = doubleArrayOf(.5, 1.0, 1.2, 1.5, 2.0)
    private val bellWeights = doubleArrayOf(.12, .42, .18, .12, .16)
    private val bowlRatios = doubleArrayOf(1.0, 2.78, 5.12, 8.15, 11.8)
    private val bowlWeights = doubleArrayOf(.48, .25, .13, .09, .05)
    private val phases = DoubleArray(10)
    private var frequency = 528.0
    private var age = 0
    fun trigger() { age = 0 }
    fun next(hz: Double, ringSeconds: Int = 16, intervalSeconds: Int = 24, bowl: Boolean = false): Float {
        frequency += (hz - frequency) * .0005
        val ring = ringSeconds.coerceIn(2, 60)
        val interval = max(intervalSeconds.coerceIn(4, 300), ring)
        val totalFrames = rate * interval
        val t = age.toDouble() / rate
        val attack = (t / .025).coerceIn(0.0, 1.0)
        val release = ((ring - t) / .20).coerceIn(0.0, 1.0)
        val ratios = if (bowl) bowlRatios else bellRatios
        val weights = if (bowl) bowlWeights else bellWeights
        var sum = 0.0
        for (i in ratios.indices) {
            val decay = if (bowl) (0.6 + i * .15) else (1.2 + i * .25)
            val normalizedDecay = decay * t / (ring / 4.0)
            val phaseIndex = i * 2
            val fundamentalHz = (frequency * ratios[i]).coerceAtMost(rate * .46)
            sum += weights[i] * sin(phases[phaseIndex]) * exp(-normalizedDecay)
            phases[phaseIndex] = (phases[phaseIndex] + 2 * PI * fundamentalHz / rate) % (2 * PI)
            if (bowl) {
                val pairHz = (fundamentalHz + .5).coerceAtMost(rate * .46)
                sum += weights[i] * 0.60 * sin(phases[phaseIndex + 1]) * exp(-normalizedDecay)
                phases[phaseIndex + 1] = (phases[phaseIndex + 1] + 2 * PI * pairHz / rate) % (2 * PI)
            }
        }
        age = (age + 1) % totalFrames
        return (sum * attack * release * (if (bowl) .58 else 1.0)).toFloat().coerceIn(-1f, 1f)
    }
}

/** RBJ peaking biquads, independent stereo state; gain smoothing is block-rate. */
class EqualizerDsp(private val rate: Int) {
    private val filters = Array(2) { Array(AcousticDsp.bands.size) { Biquad() } }
    private val gains = FloatArray(AcousticDsp.bands.size)
    fun configure(target: List<Float>) {
        for (i in gains.indices) {
            gains[i] += (target[i] - gains[i]) * .12f
            for (channel in filters) channel[i].configure(AcousticDsp.bands[i], gains[i].toDouble(), rate)
        }
    }
    fun process(input: Float, channel: Int): Float {
        var value = input.toDouble()
        for (filter in filters[channel]) value = filter.process(value)
        return value.toFloat().coerceIn(-.92f, .92f)
    }
    private class Biquad {
        var b0 = 1.0; var b1 = 0.0; var b2 = 0.0; var a1 = 0.0; var a2 = 0.0
        var z1 = 0.0; var z2 = 0.0
        fun configure(hz: Double, db: Double, rate: Int) {
            val a = 10.0.pow(db / 40); val w = 2 * PI * hz / rate
            val alpha = sin(w) / 2 // Q = 1, octave-spaced controls.
            val a0 = 1 + alpha / a
            b0 = (1 + alpha * a) / a0; b1 = -2 * cos(w) / a0; b2 = (1 - alpha * a) / a0
            a1 = b1; a2 = (1 - alpha / a) / a0
        }
        fun process(x: Double): Double {
            val y = b0 * x + z1
            z1 = b1 * x - a1 * y + z2; z2 = b2 * x - a2 * y
            return y
        }
    }
}
