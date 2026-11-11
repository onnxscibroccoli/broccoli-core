package com.parallax.entrainment

import kotlin.math.*

/**
 * Compare emitted and microphone-captured spectra, not raw PCM phases.
 * Android playback/capture clocks are not synchronized and mic gain is unknown.
 * A spectral similarity percentage is NOT calibrated loudness or proof of hearing.
 *
 * This pure implementation accepts synthetic inputs for deterministic JVM tests.
 */
object LiveAudioMatcher {
    const val RATE = 44100
    const val WINDOW = 4096
    private val edges = doubleArrayOf(90.0, 135.0, 202.0, 302.0, 453.0, 679.0,
        1018.0, 1527.0, 2290.0, 3435.0, 5153.0, 7730.0, 10200.0)

    data class Match(
        val valid: Boolean,
        val scorePercent: Int,
        val confidencePercent: Int,
        val activeBands: Int,
        val referenceRms: Double,
        val micRms: Double,
        val relativeLevelDb: Double,
        val correctionDb: List<Float?>,
        val reason: String
    )

    fun compare(reference: FloatArray, captured: ShortArray): Match {
        require(reference.size == WINDOW && captured.size == WINDOW)
        val expected = rms(reference)
        val observed = rms(captured)
        fun reject(reason: String) = Match(false, 0, 0, 0, expected, observed,
            0.0, List(7) { null }, reason)
        if (expected < .00020) return reject("Parallax audio is silent or too quiet for comparison")
        if (observed < .00018) return reject("Microphone signal is too weak")
        val clipCount = captured.count { abs(it.toInt()) >= 32000 }
        if (clipCount > WINDOW / 200) return reject("Microphone clipping; lower the media volume")

        val expectedBands = spectrum(reference)
        val micBands = spectrum(FloatArray(WINDOW) { captured[it] / 32768f })
        val peakExpected = expectedBands.maxOrNull() ?: 0.0
        if (peakExpected <= 1e-12) return reject("No audible spectrum in reference")
        val active = expectedBands.indices.filter { expectedBands[it] > peakExpected * .002 }
        if (active.isEmpty()) return reject("No measurable reference bands")

        val refTotal = expectedBands.sum().coerceAtLeast(1e-16)
        val micTotal = micBands.sum().coerceAtLeast(1e-16)
        var affinity = 0.0
        for (i in expectedBands.indices) {
            affinity += sqrt(expectedBands[i] / refTotal * micBands[i] / micTotal)
        }
        val inBandFraction = active.sumOf { micBands[it] } / micTotal
        val score = (100.0 * (.75 * affinity + .25 * inBandFraction)).roundToInt().coerceIn(0, 100)
        val confidence = (100.0 * inBandFraction *
            (active.size.toDouble() / 4.0).coerceIn(.35, 1.0)).roundToInt().coerceIn(0, 100)
        val levelDb = 20 * log10(observed.coerceAtLeast(1e-12) / expected.coerceAtLeast(1e-12))

        // Correction advice is only available when genuinely broadband, confident
        // and strong. The caller gates any automatic updates further in time.
        val pairs = AcousticDsp.bands.map { hz ->
            val i = (0 until edges.size - 1).firstOrNull { hz >= edges[it] && hz < edges[it + 1] }
            if (i == null || expectedBands[i] < peakExpected * .004 ||
                micBands[i] <= micTotal * .002) null
            else 10 * log10(micBands[i] / expectedBands[i].coerceAtLeast(1e-16))
        }
        val known = pairs.filterNotNull()
        val corrections: List<Float?> = if (known.size >= 4 && score >= 78 && confidence >= 60) {
            val median = known.sorted()[known.size / 2]
            pairs.map { db -> db?.let { (median - it).coerceIn(-6.0, 0.0).toFloat() } }
        } else List(7) { null }
        return Match(true, score, confidence, active.size, expected, observed, levelDb,
            corrections, "Spectral similarity; not an absolute acoustic calibration")
    }

    private fun rms(values: FloatArray): Double =
        sqrt(values.sumOf { it.toDouble() * it.toDouble() } / values.size)
    private fun rms(values: ShortArray): Double =
        sqrt(values.sumOf { (it / 32768.0) * (it / 32768.0) } / values.size)

    private fun spectrum(samples: FloatArray): DoubleArray {
        val real = DoubleArray(WINDOW)
        val imag = DoubleArray(WINDOW)
        for (i in samples.indices) {
            real[i] = samples[i].toDouble() * (0.5 - 0.5 * cos(2 * PI * i / (WINDOW - 1)))
        }
        // Iterative radix-2 Cooley-Tukey FFT.
        var j = 0
        for (i in 1 until WINDOW) {
            var bit = WINDOW ushr 1
            while (j and bit != 0) { j = j xor bit; bit = bit ushr 1 }
            j = j xor bit
            if (i < j) {
                val t = real[i]; real[i] = real[j]; real[j] = t
            }
        }
        var length = 2
        while (length <= WINDOW) {
            val theta = -2 * PI / length
            val half = length / 2
            var start = 0
            while (start < WINDOW) {
                for (k in 0 until half) {
                    val angle = theta * k
                    val c = cos(angle); val s = sin(angle)
                    val a = start + k; val b = a + half
                    val tr = c * real[b] - s * imag[b]
                    val ti = s * real[b] + c * imag[b]
                    real[b] = real[a] - tr; imag[b] = imag[a] - ti
                    real[a] += tr; imag[a] += ti
                }
                start += length
            }
            length = length shl 1
        }
        val bands = DoubleArray(edges.size - 1)
        for (bin in 1..WINDOW / 2) {
            val hz = bin.toDouble() * RATE / WINDOW
            val band = (0 until bands.size).firstOrNull { hz >= edges[it] && hz < edges[it + 1] }
            if (band != null) bands[band] += real[bin] * real[bin] + imag[bin] * imag[bin]
        }
        return bands
    }
}

/** Pure mapping for Parallax's original radial-gradient entities, never sonar rings. */
object AudioReactiveMapping {
    data class Parameters(val radialScale: Float, val radiusScale: Float, val intensityScale: Float)
    fun fromAmplitude(level: Float, strength: Float = .6f): Parameters {
        val a = (if (level.isFinite()) level else 0f).coerceIn(0f, 1f) *
            (if (strength.isFinite()) strength else 0f).coerceIn(0f, 1f)
        return Parameters(1f + .38f * a, 1f + .20f * a, 1f + .42f * a)
    }
}
