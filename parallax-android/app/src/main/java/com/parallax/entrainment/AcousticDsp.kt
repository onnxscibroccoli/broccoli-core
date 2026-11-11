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

    fun microCorrection(old: List<Float>, target: List<Float>) = old.indices.map {
        (old[it] + (target[it] - old[it]).coerceIn(-0.5f, 0.5f)).coerceIn(-6f, 0f)
    }
}

class BellSynth(private val rate: Int) {
    private val ratios = doubleArrayOf(.5, 1.0, 1.2, 1.5, 2.0)
    private val weights = doubleArrayOf(.12, .42, .18, .12, .16)
    private val phases = DoubleArray(5)
    private var frequency = 528.0
    private var age = 0
    fun next(hz: Double): Float {
        frequency += (hz - frequency) * .0005 // Smooth preset changes, preserving oscillator phase.
        val t = age.toDouble() / rate
        val attack = min(t / .025, 1.0)
        val release = min((4.0 - t) / .1, 1.0).coerceAtLeast(0.0)
        var sum = 0.0
        for (i in phases.indices) {
            sum += weights[i] * sin(phases[i]) * exp(-t * (1.0 + i * .3))
            phases[i] = (phases[i] + 2 * PI * frequency * ratios[i] / rate) % (2 * PI)
        }
        age = (age + 1) % (rate * 4)
        return (sum * attack * release).toFloat()
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
