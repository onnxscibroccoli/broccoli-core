package com.parallax.entrainment

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class LiveAudioMatcherTest {
    private fun wave(freqs: DoubleArray): FloatArray = FloatArray(LiveAudioMatcher.WINDOW) { i ->
        (freqs.sumOf { .08 * sin(2 * PI * it * i / LiveAudioMatcher.RATE) }).toFloat()
    }
    private fun mic(values: FloatArray, phaseShift: Int = 0): ShortArray =
        ShortArray(LiveAudioMatcher.WINDOW) { i ->
            (values[(i + phaseShift) % values.size] * 19000).roundToInt().coerceIn(-32767, 32767).toShort()
        }

    @Test fun similarSpectrumSurvivesPhaseShiftAndMicrophoneGain() {
        val x = wave(doubleArrayOf(240.0, 530.0, 1030.0, 2110.0))
        val match = LiveAudioMatcher.compare(x, mic(x, 173))
        assertTrue(match.reason, match.valid)
        assertTrue("expected high spectral similarity: ${match.scorePercent}",
            match.scorePercent >= 80)
    }

    @Test fun unrelatedFrequenciesScoreLower() {
        val x = wave(doubleArrayOf(250.0, 520.0, 1020.0, 2100.0))
        val y = wave(doubleArrayOf(3700.0, 6500.0, 7100.0))
        val similar = LiveAudioMatcher.compare(x, mic(x))
        val different = LiveAudioMatcher.compare(x, mic(y))
        assertTrue(similar.scorePercent > different.scorePercent + 15)
    }

    @Test fun silentWeakAndClippingAreUnreliableNotFalseMatches() {
        assertFalse(LiveAudioMatcher.compare(FloatArray(4096), ShortArray(4096)).valid)
        assertFalse(LiveAudioMatcher.compare(wave(doubleArrayOf(500.0)), ShortArray(4096)).valid)
        assertFalse(LiveAudioMatcher.compare(wave(doubleArrayOf(500.0)),
            ShortArray(4096) { 32767 }).valid)
    }

    @Test fun visualReactivityReturnsToBaselineWhenSilentAndClamps() {
        val still = AudioReactiveMapping.fromAmplitude(0f)
        assertEquals(1f, still.radialScale, 0f)
        assertEquals(1f, still.radiusScale, 0f)
        assertEquals(1f, still.intensityScale, 0f)
        val loud = AudioReactiveMapping.fromAmplitude(1f)
        assertTrue(loud.radialScale > 1f && loud.radiusScale > 1f && loud.intensityScale > 1f)
        assertTrue(AudioReactiveMapping.fromAmplitude(Float.NaN).radialScale.isFinite())
        assertEquals(loud, AudioReactiveMapping.fromAmplitude(99f))
    }
}
