package com.parallax.entrainment

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import kotlin.concurrent.thread
import kotlin.math.PI
import kotlin.math.sin

/**
 * Small streaming binaural-tone engine.
 *
 * The audio worker owns writes, uses bounded buffers, preserves phase across live
 * setting changes, and fades in/out to avoid clicks when sessions are changed.
 */
class AndroidAudioEngine(
    context: Context,
    targetHz: Float,
    seedStr: String,
    volume: Float,
    private val audioMode: Int
) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    @Volatile private var targetHz = targetHz.coerceIn(0.5f, 40f)
    @Volatile private var seedStr = seedStr
    @Volatile private var volume = volume.coerceIn(0f, 1f)
    @Volatile private var playing = false
    @Volatile private var stopRequested = false

    private val sampleRate = 44_100
    private val carrierHz = 210.0
    private var track: AudioTrack? = null
    private var worker: Thread? = null
    private var focusRequest: AudioFocusRequest? = null
    private val focusListener = AudioManager.OnAudioFocusChangeListener { /* Other apps handle our duck request. */ }

    fun start() {
        if (audioMode == OverlayService.AUDIO_MODE_OFF || volume <= 0f || playing) return
        if (audioMode == OverlayService.AUDIO_MODE_DUCK && !requestDuckingFocus()) return

        val minimumBytes = AudioTrack.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_OUT_STEREO,
            AudioFormat.ENCODING_PCM_FLOAT
        )
        if (minimumBytes <= 0) {
            abandonAudioFocus()
            return
        }

        val bufferBytes = maxOf(minimumBytes, 2048 * 2 * 4)
        val created = runCatching {
            AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                        .setSampleRate(sampleRate)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO)
                        .build()
                )
                .setBufferSizeInBytes(bufferBytes)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build()
        }.getOrNull()

        if (created == null || created.state != AudioTrack.STATE_INITIALIZED) {
            runCatching { created?.release() }
            abandonAudioFocus()
            return
        }

        track = created
        stopRequested = false
        playing = true
        runCatching { created.play() }.onFailure {
            playing = false
            runCatching { created.release() }
            track = null
            abandonAudioFocus()
            return
        }

        worker = thread(start = true, name = "ParallaxAudio", priority = Thread.NORM_PRIORITY - 1) {
            val frames = 1024
            val buffer = FloatArray(frames * 2)
            var sample = 0L
            var fadeInFrames = 0
            var fadeOutFrames = sampleRate / 8
            var leftPhase = 0.0
            var rightPhase = 0.0
            try {
                while (playing || fadeOutFrames > 0) {
                    val hz = targetHz.toDouble().coerceIn(0.5, 40.0)
                    val seedOffset = ((seedStr.hashCode() and 0x7fffffff) % 3000) / 100.0 - 15.0
                    val leftHz = (carrierHz + seedOffset).coerceIn(180.0, 240.0)
                    val rightHz = (leftHz + hz).coerceIn(180.5, 280.0)
                    val baseGain = (volume * 0.82f).coerceIn(0f, 0.82f)

                    for (frame in 0 until frames) {
                        val envelope = when {
                            playing -> {
                                val value = (fadeInFrames.toFloat() / (sampleRate / 5f)).coerceIn(0f, 1f)
                                if (fadeInFrames < sampleRate / 5) fadeInFrames++
                                value
                            }
                            else -> {
                                val value = (fadeOutFrames.toFloat() / (sampleRate / 8f)).coerceIn(0f, 1f)
                                if (fadeOutFrames > 0) fadeOutFrames--
                                value
                            }
                        }
                        val gain = baseGain * envelope
                        // Leave headroom and clamp floating-point samples before AudioTrack conversion.
                        buffer[frame * 2] = (sin(leftPhase).toFloat() * gain).coerceIn(-0.92f, 0.92f)
                        buffer[frame * 2 + 1] = (sin(rightPhase).toFloat() * gain).coerceIn(-0.92f, 0.92f)
                        leftPhase += 2.0 * PI * leftHz / sampleRate
                        rightPhase += 2.0 * PI * rightHz / sampleRate
                        if (leftPhase >= 2.0 * PI) leftPhase -= 2.0 * PI
                        if (rightPhase >= 2.0 * PI) rightPhase -= 2.0 * PI
                        sample++
                    }
                    val activeTrack = track ?: break
                    val written = activeTrack.write(buffer, 0, buffer.size, AudioTrack.WRITE_BLOCKING)
                    if (written < 0) break
                    if (!playing && fadeOutFrames <= 0) break
                }
            } catch (_: IllegalStateException) {
                // A device audio route can disappear while the service is running.
            } finally {
                playing = false
                val finishedTrack = track
                track = null
                runCatching { finishedTrack?.stop() }
                runCatching { finishedTrack?.release() }
                abandonAudioFocus()
            }
        }
    }

    fun update(targetHz: Float, seedStr: String, volume: Float) {
        this.targetHz = targetHz.coerceIn(0.5f, 40f)
        this.seedStr = seedStr
        this.volume = volume.coerceIn(0f, 1f)
    }

    fun stop() {
        if (!playing && worker == null) {
            abandonAudioFocus()
            return
        }
        stopRequested = true
        playing = false
        val runningWorker = worker
        if (runningWorker != null && runningWorker !== Thread.currentThread()) {
            runCatching { runningWorker.join(450L) }
        }
        if (runningWorker?.isAlive == false) worker = null
        if (runningWorker?.isAlive == true) {
            // Last-resort cleanup for a driver that does not return from a blocking write.
            val unfinished = track
            track = null
            runCatching { unfinished?.stop() }
            runCatching { unfinished?.release() }
            worker = null
        }
        abandonAudioFocus()
    }

    private fun requestDuckingFocus(): Boolean {
        return if (Build.VERSION.SDK_INT >= 26) {
            val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                .setOnAudioFocusChangeListener(focusListener)
                .setWillPauseWhenDucked(false)
                .build()
            focusRequest = request
            audioManager.requestAudioFocus(request) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
        } else {
            @Suppress("DEPRECATION")
            audioManager.requestAudioFocus(
                focusListener,
                AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
            ) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
        }
    }

    private fun abandonAudioFocus() {
        if (Build.VERSION.SDK_INT >= 26) {
            focusRequest?.let { runCatching { audioManager.abandonAudioFocusRequest(it) } }
            focusRequest = null
        } else {
            @Suppress("DEPRECATION")
            runCatching { audioManager.abandonAudioFocus(focusListener) }
        }
    }
}
