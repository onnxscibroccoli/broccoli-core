package com.parallax.entrainment

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.abs

class FmcwSonarDspTest {
    @Test fun chirpHasCorrectLengthBoundAndResolution() {
        val c = FmcwSonarDsp.chirp()
        assertEquals(960, c.size)
        assertTrue(c.all { it.isFinite() && abs(it) <= 1f })
        assertEquals(.042875, FmcwSonarDsp.fundamentalRangeResolutionMeters(), .000001)
    }

    @Test fun matchedFilterDetectsSyntheticSingleEchoRelativeToDirectLeak() {
        val signal = FloatArray(7000)
        val chirp = FmcwSonarDsp.chirp()
        val direct = 600
        val delay = 400 // ~1.43m round-trip relative propagation
        for (i in chirp.indices) {
            signal[direct + i] += chirp[i] * .70f
            signal[direct + delay + i] += chirp[i] * .45f
        }
        val echo = FmcwSonarDsp.estimate(signal)
        assertNotNull("echo should be observed after direct leakage", echo)
        assertEquals(delay * 343.0 / (2.0 * 48000), echo!!.rangeMeters, .055)
        assertTrue(echo.directCorrelation >= .15)
    }

    @Test fun rejectsSilenceAndUninterpretableInput() {
        assertNull(FmcwSonarDsp.estimate(FloatArray(6000)))
        assertNull(FmcwSonarDsp.estimate(FloatArray(100)))
    }
}
