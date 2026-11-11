package com.parallax.entrainment

import android.os.SystemClock

/** One immutable, short-lived PCM reference window. Never persisted or sent off device. */
data class PlaybackReference(
    val mono: FloatArray,
    val timestampMs: Long,
    val builtInSpeaker: Boolean,
    val generation: Long
)

/**
 * Non-blocking bridge from Parallax's own audio worker to the meter/visuals.
 * The producer creates a snapshot only while continuous mic comparison is on.
 * The source is POST-EQ and POST-volume: what was actually written to AudioTrack.
 */
object PlaybackReferenceBus {
    @Volatile var visualAmplitude: Float = 0f; private set
    @Volatile var sessionPlaying: Boolean = false; private set
    @Volatile var builtInSpeaker: Boolean = false; private set
    @Volatile var comparisonRequested: Boolean = false
    @Volatile var monitorRunning: Boolean = false
    @Volatile var status: String = "Live comparison is off. Microphone is not in use."
    @Volatile var lastMatchPercent: Int? = null; private set
    @Volatile var lastConfidencePercent: Int = 0; private set
    @Volatile var reference: PlaybackReference? = null; private set
    @Volatile private var generation: Long = 0L

    @Synchronized fun begin(): Long {
        generation++
        sessionPlaying = true
        visualAmplitude = 0f
        builtInSpeaker = false
        reference = null
        return generation
    }

    /** Called at buffer boundaries, not per sample. */
    fun level(id: Long, amplitude: Float, speaker: Boolean) {
        if (generation != id) return
        visualAmplitude = (if (amplitude.isFinite()) amplitude else 0f).coerceIn(0f, 1f)
        builtInSpeaker = speaker
    }

    fun capture(id: Long, pcm: FloatArray, speaker: Boolean) {
        if (generation != id || !comparisonRequested || !sessionPlaying) return
        reference = PlaybackReference(pcm, SystemClock.elapsedRealtime(), speaker, id)
    }

    fun freshSpeakerReference(): PlaybackReference? {
        val current = reference ?: return null
        if (!sessionPlaying || generation != current.generation || !builtInSpeaker ||
            !current.builtInSpeaker || SystemClock.elapsedRealtime() - current.timestampMs > 800L
        ) return null
        return current
    }

    fun meter(score: Int?, confidence: Int, description: String) {
        lastMatchPercent = score
        lastConfidencePercent = confidence.coerceIn(0, 100)
        status = description
    }

    @Synchronized fun finish(id: Long) {
        if (generation != id) return
        sessionPlaying = false
        builtInSpeaker = false
        visualAmplitude = 0f
        reference = null
        lastMatchPercent = null
        lastConfidencePercent = 0
    }

    fun clearMonitor() {
        comparisonRequested = false
        monitorRunning = false
        lastMatchPercent = null
        lastConfidencePercent = 0
        status = "Live comparison stopped. Microphone released."
    }
}
