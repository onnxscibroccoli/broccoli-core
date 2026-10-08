package com.parallax.entrainment

import android.content.Context
import android.content.res.Configuration
import android.graphics.*
import android.view.Choreographer
import android.view.View
import kotlin.math.cos
import kotlin.math.sin

/**
 * Canvas renderer intentionally mirrors the original HTML engine:
 * - Mulberry32 + hashSeedStr deterministic seeding
 * - 5 colored WaveEntity instances + 3 shadow instances
 * - identical radius/velocity/angle/speed/amplitude ranges
 * - target-Hz pulse drives the same visual breathing factor
 * - light/dark palettes match the CSS renderer
 *
 * It remains a normal hardware-accelerated View paced by Choreographer,
 * preserving the Android 15 lifecycle/input fix from PR #72.
 */
class EntrainmentSurfaceView(
    context: Context,
    private val isFullOverlay: Boolean,
    private val targetHz: Float,
    seedStr: String
) : View(context), Choreographer.FrameCallback {

    private data class WaveEntity(
        val isShadow: Boolean,
        var x: Float = 0f,
        var y: Float = 0f,
        var vx: Float = 0f,
        var vy: Float = 0f,
        var radius: Float = 0f,
        var hue: Float = 0f,
        var angleX: Float = 0f,
        var angleY: Float = 0f,
        var speedX: Float = 0f,
        var speedY: Float = 0f,
        var amp: Float = 0f
    )

    private class Mulberry32(seed: Int) {
        private var a = seed

        private fun imul(x: Int, y: Int): Int =
            ((x.toLong() * y.toLong()) and 0xffffffffL).toInt()

        fun nextFloat(): Float {
            a += 0x6D2B79F5
            var t = a
            t = imul(t xor (t ushr 15), t or 1)
            t = t xor (t + imul(t xor (t ushr 7), t or 61))
            return ((t xor (t ushr 14)).toUInt().toLong() / 4294967296.0).toFloat()
        }
    }

    private val choreographer = Choreographer.getInstance()
    private val entities = ArrayList<WaveEntity>(8)
    private val entityPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var running = false
    private var startNanos = 0L
    private var seedText = seedStr

    private val darkMode: Boolean
        get() = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
            Configuration.UI_MODE_NIGHT_YES

    init {
        setLayerType(View.LAYER_TYPE_HARDWARE, null)
        setBackgroundColor(Color.TRANSPARENT)
        initEntities(seedText)
    }

    private fun hashSeedStr(str: String): Int {
        var hash = 0
        for (ch in str) {
            hash = 31 * hash + ch.code
        }
        return hash
    }

    private fun initEntities(seed: String) {
        seedText = seed
        val rng = Mulberry32(hashSeedStr(seed))
        entities.clear()

        repeat(5) {
            entities += WaveEntity(isShadow = false).also { reset(it, rng, width, height) }
        }
        repeat(3) {
            entities += WaveEntity(isShadow = true).also { reset(it, rng, width, height) }
        }
    }

    private fun reset(entity: WaveEntity, rng: Mulberry32, w: Int, h: Int) {
        val maxDimension = maxOf(w, h, 1).toFloat()
        entity.x = rng.nextFloat() * w.coerceAtLeast(1)
        entity.y = rng.nextFloat() * h.coerceAtLeast(1)
        entity.vx = (rng.nextFloat() - 0.5f) * 0.6f
        entity.vy = (rng.nextFloat() - 0.5f) * 0.6f
        entity.radius = (rng.nextFloat() * 0.3f + 0.3f) * maxDimension
        entity.hue = rng.nextFloat() * 360f
        entity.angleX = rng.nextFloat() * (Math.PI * 2.0).toFloat()
        entity.angleY = rng.nextFloat() * (Math.PI * 2.0).toFloat()
        entity.speedX = rng.nextFloat() * 0.003f + 0.0015f
        entity.speedY = rng.nextFloat() * 0.003f + 0.0015f
        entity.amp = rng.nextFloat() * 1.5f + 1.2f
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (oldw == 0 && oldh == 0) initEntities(seedText)
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        startRendering()
    }

    override fun onDetachedFromWindow() {
        stopRendering()
        super.onDetachedFromWindow()
    }

    private fun startRendering() {
        if (running) return
        running = true
        startNanos = System.nanoTime()
        choreographer.removeFrameCallback(this)
        choreographer.postFrameCallback(this)
    }

    private fun stopRendering() {
        running = false
        choreographer.removeFrameCallback(this)
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running) return
        invalidate()
        choreographer.postFrameCallback(this)
    }

    private fun hslToColor(hue: Float, saturation: Float, lightness: Float, alpha: Int): Int {
        val h = ((hue % 360f) + 360f) % 360f / 360f
        val s = saturation.coerceIn(0f, 1f)
        val l = lightness.coerceIn(0f, 1f)

        if (s == 0f) {
            val v = (l * 255f).toInt().coerceIn(0, 255)
            return Color.argb(alpha, v, v, v)
        }

        val q = if (l < 0.5f) l * (1f + s) else l + s - l * s
        val p = 2f * l - q

        fun hueToRgb(t0: Float): Float {
            var t = t0
            if (t < 0f) t += 1f
            if (t > 1f) t -= 1f
            return when {
                t < 1f / 6f -> p + (q - p) * 6f * t
                t < 1f / 2f -> q
                t < 2f / 3f -> p + (q - p) * (2f / 3f - t) * 6f
                else -> p
            }
        }

        return Color.argb(
            alpha,
            (hueToRgb(h + 1f / 3f) * 255f).toInt().coerceIn(0, 255),
            (hueToRgb(h) * 255f).toInt().coerceIn(0, 255),
            (hueToRgb(h - 1f / 3f) * 255f).toInt().coerceIn(0, 255)
        )
    }

    private fun drawWaveEntity(canvas: Canvas, entity: WaveEntity, pulseFactor: Float) {
        val alpha = if (entity.isShadow) {
            (0.35f + pulseFactor * 0.15f)
        } else {
            (0.42f + pulseFactor * 0.20f)
        }
        val centerColor: Int
        val edgeColor: Int

        if (entity.isShadow) {
            if (darkMode) {
                centerColor = Color.argb((alpha * 255f).toInt(), 210, 210, 205)
            } else {
                centerColor = Color.argb((alpha * 255f).toInt(), 110, 110, 105)
            }
            edgeColor = Color.TRANSPARENT
        } else if (darkMode) {
            centerColor = hslToColor(entity.hue, 0.65f, 0.48f, (alpha * 255f).toInt())
            edgeColor = hslToColor(entity.hue, 0.55f, 0.25f, 0)
        } else {
            centerColor = hslToColor(entity.hue, 0.55f, 0.72f, (alpha * 255f).toInt())
            edgeColor = hslToColor(entity.hue, 0.45f, 0.80f, 0)
        }

        entityPaint.shader = RadialGradient(
            entity.x,
            entity.y,
            entity.radius,
            centerColor,
            edgeColor,
            Shader.TileMode.CLAMP
        )
        canvas.drawCircle(entity.x, entity.y, entity.radius, entityPaint)
        entityPaint.shader = null
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val elapsed = if (startNanos == 0L) 0.0
        else (System.nanoTime() - startNanos) / 1_000_000_000.0

        val w = width
        val h = height
        if (w <= 0 || h <= 0) return

        val pulseFactor =
            ((sin(2.0 * Math.PI * targetHz.toDouble() * elapsed) + 1.0) * 0.5).toFloat()

        canvas.save()

        // The original HTML is a full-viewport renderer. Border mode remains
        // available for the mobile overlay, but uses the same underlying math.
        if (!isFullOverlay && w > 96 && h > 96) {
            canvas.clipOutRect(48f, 48f, (w - 48).toFloat(), (h - 48).toFloat())
        }

        // Reproduce the HTML page's light/dark base palette while keeping the
        // Android window itself translucent so the overlay remains composited.
        entityPaint.shader = null
        entityPaint.color = if (darkMode) Color.rgb(27, 27, 28) else Color.rgb(228, 228, 227)
        entityPaint.alpha = 255
        canvas.drawRect(0f, 0f, w.toFloat(), h.toFloat(), entityPaint)

        // CSS canvas uses filter: blur(60px). A hardware View cannot apply the
        // exact DOM filter cheaply, so use software-compatible blur via a
        // second translucent pass. The large radii are already soft radial
        // gradients, which preserves the visual result without a SurfaceView.
        entities.forEach { entity ->
            entity.angleX += entity.speedX
            entity.angleY += entity.speedY
            entity.x += sin(entity.angleX.toDouble()).toFloat() * entity.amp + entity.vx
            entity.y += cos(entity.angleY.toDouble()).toFloat() * entity.amp + entity.vy
            entity.hue += 0.1f

            if (entity.x < -entity.radius) entity.x = w + entity.radius
            if (entity.x > w + entity.radius) entity.x = -entity.radius
            if (entity.y < -entity.radius) entity.y = h + entity.radius
            if (entity.y > h + entity.radius) entity.y = -entity.radius

            drawWaveEntity(canvas, entity, pulseFactor)
        }

        // Match the original canvas opacity of 0.90 by fading the renderer's
        // result toward the base page color. The Android window itself is also
        // constrained to alpha 0.75 for Android 15 obscuring-touch safety.
        entityPaint.shader = null
        entityPaint.color = if (darkMode) Color.rgb(27, 27, 28) else Color.rgb(228, 228, 227)
        entityPaint.alpha = (255f * 0.10f).toInt()
        canvas.drawRect(0f, 0f, w.toFloat(), h.toFloat(), entityPaint)

        entityPaint.alpha = 255
        canvas.restore()
    }
}
