package com.parallax.entrainment

import kotlin.math.*

/**
 * Bounded, allocation-free-per-sample reference DSP for an opt-in near-ultrasound
 * single-device test. NOT a calibrated depth camera or presence classifier.
 *
 * A direct speaker-to-microphone path acts as the timing anchor because Android
 * input/output pipelines do not share a guaranteed common sample-clock epoch.
 */
object FmcwSonarDsp {
    const val RATE = 48000
    const val CHIRP_SAMPLES = 960
    const val LOW_HZ = 17500.0
    const val HIGH_HZ = 21500.0
    const val SOUND_M_PER_SECOND = 343.0

    data class Echo(
        val rangeMeters: Double,
        val directCorrelation: Double,
        val echoCorrelation: Double,
        val directSample: Int,
        val echoSample: Int
    )

    fun chirp(): FloatArray = FloatArray(CHIRP_SAMPLES) { i ->
        val t = i.toDouble() / RATE
        val duration = CHIRP_SAMPLES.toDouble() / RATE
        // Gentle raised-cosine attack/release to limit audible clicks.
        val envelope = sin(PI * i / (CHIRP_SAMPLES - 1)).pow(2.0)
        (sin(2 * PI * (LOW_HZ * t + (HIGH_HZ - LOW_HZ) * t * t / (2 * duration))) * envelope).toFloat()
    }

    private fun projection(samples: FloatArray, template: FloatArray, offset: Int): Double {
        var sum = 0.0
        for (j in template.indices) sum += samples[offset + j] * template[j]
        return sum
    }

    private fun score(samples: FloatArray, template: FloatArray, templateEnergy: Double, at: Int): Double {
        var signalEnergy = 0.0
        for (j in template.indices) {
            val x = samples[at + j]
            signalEnergy += x * x
        }
        if (signalEnergy < 1e-10) return 0.0
        return abs(projection(samples, template, at)) / sqrt(templateEnergy * signalEnergy)
    }

    /**
     * Matched-filter prototype. Requires one isolated chirp and subsequent echoes.
     * Inputs are in-memory PCM normalized to [-1, 1]. No voice/audio retention.
     * The first high-correlation return is normally direct leakage; a later
     * separated return suggests a reflective path but is NOT a verified obstacle.
     */
    fun estimate(samples: FloatArray): Echo? {
        val chirp = chirp()
        if (samples.size < CHIRP_SAMPLES + 1800) return null
        val energy = chirp.sumOf { it.toDouble() * it.toDouble() }
        val latest = samples.size - CHIRP_SAMPLES - 1200
        var direct = -1; var best = 0.0
        for (at in 0..latest step 8) {
            val result = score(samples, chirp, energy, at)
            if (result > best) { best = result; direct = at }
        }
        if (direct < 0 || best < 0.15) return null
        var refined = direct
        for (at in max(0, direct - 8)..min(latest, direct + 8)) {
            val result = score(samples, chirp, energy, at)
            if (result > best) { best = result; refined = at }
        }
        direct = refined
        // Remove the strongest direct path in a scratch buffer to limit leakage.
        val residual = samples.copyOf()
        val amplitude = projection(samples, chirp, direct) / energy
        for (i in chirp.indices) residual[direct + i] -= (amplitude * chirp[i]).toFloat()
        val minLag = (2.0 * .35 / SOUND_M_PER_SECOND * RATE).toInt()  // ~35 cm blind zone
        val maxLag = min(900, residual.size - CHIRP_SAMPLES - direct)
        if (maxLag <= minLag) return null
        var echoAt = -1; var echoScore = 0.0
        for (lag in minLag..maxLag) {
            val at = direct + lag
            val candidate = score(residual, chirp, energy, at)
            if (candidate > echoScore) { echoScore = candidate; echoAt = at }
        }
        if (echoAt == -1 || echoScore < 0.15) return null
        val range = (echoAt - direct) * SOUND_M_PER_SECOND / (2.0 * RATE)
        if (!range.isFinite() || range !in .35..3.3) return null
        return Echo(range, best, echoScore, direct, echoAt)
    }

    fun fundamentalRangeResolutionMeters(): Double =
        SOUND_M_PER_SECOND / (2 * (HIGH_HZ - LOW_HZ))
}
