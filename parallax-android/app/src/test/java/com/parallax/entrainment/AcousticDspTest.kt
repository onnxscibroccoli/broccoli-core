package com.parallax.entrainment

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class AcousticDspTest {
    @Test fun manualBandsWinAndUnlockedBandsFollowAuto() {
        val result = AcousticDsp.effective(List(7) { -4f }, List(7) { 3f }, List(7) { it == 2 })
        assertEquals(3f, result[2], 0f)
        assertEquals(-4f, result[1], 0f)
    }
    @Test fun peaksAreCutAndNullsNeverBoosted() {
        val measured = listOf(.01, .01, .04, .01, .001, .01, .01)
        val result = AcousticDsp.correction(List(7) { 1e-8 }, measured)!!
        assertEquals(-6f, result[2], .01f)
        assertEquals(0f, result[4], 0f)
        assertTrue(result.all { it in -6f..0f })
    }
    @Test fun silenceNoiseAndNonfiniteDataAreRejected() {
        assertNull(AcousticDsp.correction(List(7) { 0.0 }, List(7) { 0.0 }))
        assertNull(AcousticDsp.correction(List(7) { .1 }, List(7) { .2 }))
        assertNull(AcousticDsp.correction(List(7) { 0.0 }, List(7) { Double.NaN }))
    }
    @Test fun periodicStepsAreBoundedInBothDirections() {
        val result = AcousticDsp.microCorrection(listOf(0f, -6f), listOf(-6f, 0f))
        assertEquals(listOf(-.5f, -5.5f), result)
    }
    @Test fun analyzerRecoversKnownTonePowerAndRejectsOtherBand() {
        val samples = ShortArray(4096) { (sin(2 * PI * 1000 * it / 44100) * .2 * 32767).toInt().toShort() }
        assertEquals(.04, AcousticDsp.power(samples, samples.size, 1000.0, 44100), .001)
        assertTrue(AcousticDsp.power(samples, samples.size, 2000.0, 44100) < 1e-6)
    }
    @Test fun equalizerActuallyAttenuatesCenterAndKeepsChannelsIndependent() {
        val eq = EqualizerDsp(44100)
        repeat(150) { eq.configure(List(7) { if (it == 3) -6f else 0f }) }
        var inputPower = 0.0; var outputPower = 0.0
        repeat(44100) { i ->
            val x = (.1 * sin(2 * PI * 1000 * i / 44100)).toFloat()
            val y = eq.process(x, 0)
            assertEquals(0f, eq.process(0f, 1), 0f)
            if (i > 4000) { inputPower += x * x; outputPower += y * y }
        }
        assertEquals(-6.0, 10 * log10(outputPower / inputPower), .1)
    }
    @Test fun everyBellIsFiniteBoundedAndNonSilentAcrossRepeatedStrikes() {
        assertEquals(16, AcousticDsp.bells.distinct().size)
        for (hz in AcousticDsp.bells) {
            val bell = BellSynth(44100)
            var peak = 0f; var previous = 0f
            repeat(44100 * 5) {
                val value = bell.next(hz)
                assertTrue(value.isFinite() && abs(value) <= 1f)
                assertTrue(abs(value - previous) < .3f)
                previous = value; peak = max(peak, abs(value))
            }
            assertTrue(peak > .1f)
        }
    }
    @Test fun rapidEqChangesRemainFiniteAndLimited() {
        val eq = EqualizerDsp(44100)
        repeat(500) { block ->
            eq.configure(List(7) { if (block % 2 == 0) 6f else -12f })
            repeat(1024) { i ->
                val y = eq.process(sin(i.toDouble()).toFloat(), 0)
                assertTrue(y.isFinite() && abs(y) <= .92f)
            }
        }
    }
    @Test fun sonarSpectrumUsesMeasuredBandsAndRejectsInvalidInput() {
        val measured = listOf(.001, .002, .01, .1, .01, .002, .001)
        val response = AcousticDsp.normalizedSpectrum(List(7) { 1e-7 }, measured)!!
        assertEquals(7, response.size)
        assertEquals(1f, response[3], 0f)
        assertTrue(response[0] < response[3])
        assertTrue(response.all { it in 0f..1f && it.isFinite() })
        assertNull(AcousticDsp.normalizedSpectrum(List(7) { 0.0 }, List(7) { Double.NaN }))
        assertNull(AcousticDsp.normalizedSpectrum(List(7) { .2 }, List(7) { .1 }))
    }

    @Test fun bellCarriersMaintainTargetDifferenceAndLongRing() {
        val rate = 48000
        val left = BellSynth(rate)
        val right = BellSynth(rate)
        var stereoDifference = 0.0
        var energySecondFive = 0.0
        repeat(rate * 6) {
            val a = left.next(528.0, 16, 24)
            val b = right.next(534.0, 16, 24)
            stereoDifference += kotlin.math.abs(a - b)
            if (it in rate * 4 until rate * 5) energySecondFive += kotlin.math.abs(a.toDouble())
        }
        assertTrue(stereoDifference > 100.0)
        assertTrue("ring should last beyond four seconds", energySecondFive > 0.01)
    }
    @Test fun bowlSynthesisIsFiniteAndLongLived() {
        val model = BellSynth(48000)
        var nonzero = 0
        repeat(48000 * 5) {
            val value = model.next(174.0, 24, 30, true)
            assertTrue(value.isFinite() && value in -1f..1f)
            if (it > 48000 * 4 && kotlin.math.abs(value) > .00001f) nonzero++
        }
        assertTrue(nonzero > 100)
    }

    @Test fun adaptiveCalibrationKeepsUnreliableBands() {
        val n = List(7) { 1e-7 }
        val s = listOf(.001, .002, .004, .03, .001, .0001, 1e-8)
        val out = AcousticDsp.adaptiveCorrection(n, s)!!
        assertEquals(6, out.validCount)
        assertNull(out.bands[6])
        assertTrue(out.bands.dropLast(1).all { it != null && it in -6f..0f })
    }
    @Test fun adaptiveCalibrationRejectsMostlyWeakSignals() {
        assertNull(AcousticDsp.adaptiveCorrection(List(7) { 1e-4 },
            listOf(.01, 1e-4, 2e-4, 2e-4, 2e-4, 2e-4, 1e-4)))
    }

}
