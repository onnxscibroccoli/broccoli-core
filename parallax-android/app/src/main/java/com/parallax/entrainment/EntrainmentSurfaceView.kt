package com.parallax.entrainment

import android.content.Context
import android.graphics.*
import android.view.SurfaceHolder
import android.view.SurfaceView
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

class EntrainmentSurfaceView(
    context: Context,
    private val isFullOverlay: Boolean,
    private val targetHz: Float,
    seedStr: String
) : SurfaceView(context), SurfaceHolder.Callback, Runnable {

    private data class Particle(
        val radius: Float,
        val angle: Float,
        val size: Float,
        val speed: Float,
        val phase: Float,
        val orbit: Int
    )

    private var renderThread: Thread? = null
    @Volatile private var running = false
    private val surfaceHolder = holder
    private var state = seedStr.hashCode().toLong() and 0xffffffffL
    private val particles = ArrayList<Particle>(96)

    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val ringPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 1.5f
    }
    private val particlePaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val rayPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 1f
    }
    private val centerPaint = Paint(Paint.ANTI_ALIAS_FLAG)

    init {
        setZOrderOnTop(true)
        surfaceHolder.setFormat(PixelFormat.TRANSLUCENT)
        surfaceHolder.addCallback(this)
        buildParticles()
    }

    private fun nextRandom(): Float {
        state = (state + 0x6D2B79F5L) and 0xffffffffL
        var z = state
        z = (z xor (z ushr 16)) * 0x45d9f3bL and 0xffffffffL
        z = (z xor (z ushr 16)) * 0x45d9f3bL and 0xffffffffL
        z = z xor (z ushr 16)
        return (z and 0xffffffffL).toFloat() / 4294967296f
    }

    private fun buildParticles() {
        particles.clear()
        state = state xor 0x9E3779B9L
        repeat(96) { i ->
            val orbit = i % 6
            particles += Particle(
                radius = 0.10f + nextRandom() * 0.80f,
                angle = nextRandom() * (Math.PI * 2.0).toFloat(),
                size = 1.0f + nextRandom() * 3.2f,
                speed = (0.06f + nextRandom() * 0.22f) * if (orbit % 2 == 0) 1f else -1f,
                phase = nextRandom() * (Math.PI * 2.0).toFloat(),
                orbit = orbit
            )
        }
    }

    override fun run() {
        val start = System.nanoTime()
        while (running) {
            if (!surfaceHolder.surface.isValid) {
                Thread.sleep(8)
                continue
            }

            val canvas = try {
                surfaceHolder.lockCanvas()
            } catch (_: Throwable) {
                null
            } ?: continue

            try {
                val elapsed = (System.nanoTime() - start) / 1_000_000_000.0
                val w = width.toFloat()
                val h = height.toFloat()
                val cx = w * 0.5f
                val cy = h * 0.5f
                val radius = min(w, h) * 0.46f

                // The HTML version is a layered, slowly breathing radial field.
                // Keep the background transparent so the user's app remains visible.
                canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)

                if (!isFullOverlay) {
                    canvas.save()
                    canvas.clipOutRect(48f, 48f, w - 48f, h - 48f)
                }

                val pulse = ((sin(2.0 * Math.PI * targetHz * elapsed) + 1.0) * 0.5).toFloat()
                val slow = elapsed * (0.12 + targetHz * 0.0025)
                val breathe = 0.94f + pulse * 0.10f

                // Deep radial atmosphere.
                glowPaint.shader = RadialGradient(
                    cx, cy, radius * 1.12f,
                    intArrayOf(
                        Color.argb((34 + pulse * 34).toInt(), 110, 145, 255),
                        Color.argb((18 + pulse * 20).toInt(), 80, 70, 210),
                        Color.TRANSPARENT
                    ),
                    floatArrayOf(0f, 0.48f, 1f),
                    Shader.TileMode.CLAMP
                )
                canvas.drawCircle(cx, cy, radius * 1.12f, glowPaint)

                // Concentric interference rings.
                for (i in 0 until 9) {
                    val phase = (elapsed * (0.035 + targetHz * 0.0008) + i * 0.105) % 1.0
                    val rr = radius * (0.13f + i * 0.105f + phase.toFloat() * 0.045f)
                    val a = (18f + 34f * (1f - phase.toFloat()) + pulse * 18f).toInt()
                    ringPaint.color = Color.argb(a.coerceIn(0, 110), 115, 155, 255)
                    ringPaint.strokeWidth = if (i == 0) 2.2f else 1.0f
                    canvas.drawCircle(cx, cy, rr, ringPaint)
                }

                // Fine radial rays create the same hypnotic geometric texture as the HTML canvas.
                for (i in 0 until 32) {
                    val angle = i * (Math.PI * 2.0 / 32.0) + slow * if (i % 2 == 0) 1 else -1
                    val inner = radius * (0.18f + (i % 5) * 0.035f)
                    val outer = radius * (0.88f + 0.06f * sin(elapsed * 0.7 + i).toFloat())
                    val a = (12 + pulse * 20 + if (i % 4 == 0) 14 else 0).toInt()
                    rayPaint.color = Color.argb(a.coerceIn(0, 80), 135, 160, 255)
                    canvas.drawLine(
                        cx + (cos(angle) * inner).toFloat(),
                        cy + (sin(angle) * inner).toFloat(),
                        cx + (cos(angle) * outer).toFloat(),
                        cy + (sin(angle) * outer).toFloat(),
                        rayPaint
                    )
                }

                // Seeded orbiting particles. Their paths are deterministic and smooth.
                particles.forEach { p ->
                    val angle = p.angle.toDouble() + elapsed * p.speed.toDouble() + p.phase.toDouble() * 0.03
                    val wobble = 1f + 0.07f * sin(elapsed * (0.5 + p.orbit * 0.08) + p.phase.toDouble()).toFloat()
                    val rr = radius * p.radius * wobble * breathe
                    val x = cx + cos(angle.toDouble()) * rr
                    val y = cy + sin(angle.toDouble()) * rr * 0.72
                    val flicker = 0.35f + 0.65f * ((sin(elapsed * (1.2 + p.orbit * 0.15) + p.phase.toDouble()).toFloat() + 1f) * 0.5f)
                    val a = (35 + flicker * 120 + pulse * 25).toInt().coerceIn(0, 210)
                    particlePaint.color = Color.argb(a, 150, 180, 255)
                    canvas.drawCircle(x.toFloat(), y.toFloat(), p.size * (0.75f + pulse * 0.5f), particlePaint)
                }

                // Central luminous core and nested halo.
                centerPaint.shader = RadialGradient(
                    cx, cy, radius * 0.24f,
                    intArrayOf(
                        Color.argb((105 + pulse * 90).toInt(), 220, 235, 255),
                        Color.argb((48 + pulse * 55).toInt(), 135, 170, 255),
                        Color.TRANSPARENT
                    ),
                    floatArrayOf(0f, 0.22f, 1f),
                    Shader.TileMode.CLAMP
                )
                canvas.drawCircle(cx, cy, radius * 0.24f, centerPaint)
                centerPaint.shader = null

                val core = radius * (0.055f + pulse * 0.012f)
                centerPaint.color = Color.argb((150 + pulse * 80).toInt(), 225, 240, 255)
                canvas.drawCircle(cx, cy, core, centerPaint)

                if (!isFullOverlay) canvas.restore()
            } finally {
                surfaceHolder.unlockCanvasAndPost(canvas)
            }

            Thread.sleep(16)
        }
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        running = true
        renderThread = Thread(this, "ParallaxRender").also {
            it.isDaemon = true
            it.start()
        }
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        running = false
        renderThread?.interrupt()
        renderThread?.join(1000)
        renderThread = null
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) = Unit
}
