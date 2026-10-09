package com.parallax.entrainment

import android.content.Context
import android.content.res.Configuration
import android.graphics.*
import android.view.Choreographer
import android.view.View
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

class EntrainmentSurfaceView(
    context: Context,
    private val isFullOverlay: Boolean,
    private val targetHz: Float,
    seedStr: String,
    private val fullOpacity: Float = 1f,
    private val borderWidthDp: Float = 72f,
    private val borderOpacity: Float = 0.75f,
    private val flashingEnabled: Boolean = false,
    private val inverseBorderMask: Boolean = false
) : View(context), Choreographer.FrameCallback {
    private data class WaveEntity(
        val isShadow: Boolean,
        var x: Float = 0f, var y: Float = 0f, var vx: Float = 0f, var vy: Float = 0f,
        var radius: Float = 0f, var hue: Float = 0f, var angleX: Float = 0f, var angleY: Float = 0f,
        var speedX: Float = 0f, var speedY: Float = 0f, var amp: Float = 0f
    )
    private class Mulberry32(seed: Int) {
        private var a = seed
        private fun imul(x: Int, y: Int) = ((x.toLong() * y.toLong()) and 0xffffffffL).toInt()
        fun nextFloat(): Float {
            a += 0x6D2B79F5
            var t = a
            t = imul(t xor (t ushr 15), t or 1)
            t = t xor (t + imul(t xor (t ushr 7), t or 61))
            return ((t xor (t ushr 14)).toUInt().toLong() / 4294967296.0).toFloat()
        }
    }

    private val choreographer = Choreographer.getInstance()
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val borderMaskPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        xfermode = PorterDuffXfermode(PorterDuff.Mode.DST_IN)
    }
    private var borderMask: Bitmap? = null
    private var borderMaskWidth = 0
    private var borderMaskHeight = 0
    private val entities = ArrayList<WaveEntity>(8)
    private var running = false
    private var startNanos = 0L
    private var lastRenderedFrameNanos = 0L
    private val minimumFrameIntervalNanos = 33_333_333L // 30 fps caps redraw cost while keeping motion fluid.
    private var seedText = seedStr
    private val density = resources.displayMetrics.density
    private val darkMode get() = context.getSharedPreferences(OverlayService.PREFS, Context.MODE_PRIVATE)
        .getBoolean(OverlayService.KEY_DARK_THEME, true)

    init {
        setLayerType(View.LAYER_TYPE_HARDWARE, null)
        initEntities(seedText)
    }

    private fun hashSeedStr(str: String): Int {
        var h = 0
        for (c in str) h = 31 * h + c.code
        return h
    }

    private fun initEntities(seed: String) {
        seedText = seed
        val r = Mulberry32(hashSeedStr(seed))
        entities.clear()
        repeat(5) { entities += WaveEntity(false).also { reset(it, r) } }
        repeat(3) { entities += WaveEntity(true).also { reset(it, r) } }
    }

    private fun reset(e: WaveEntity, r: Mulberry32) {
        val m = maxOf(width, height, 1).toFloat()
        e.x = r.nextFloat() * width.coerceAtLeast(1)
        e.y = r.nextFloat() * height.coerceAtLeast(1)
        e.vx = (r.nextFloat() - .5f) * .6f
        e.vy = (r.nextFloat() - .5f) * .6f
        e.radius = (r.nextFloat() * .3f + .3f) * m
        e.hue = r.nextFloat() * 360f
        e.angleX = r.nextFloat() * (Math.PI * 2).toFloat()
        e.angleY = r.nextFloat() * (Math.PI * 2).toFloat()
        e.speedX = r.nextFloat() * .003f + .0015f
        e.speedY = r.nextFloat() * .003f + .0015f
        e.amp = r.nextFloat() * 1.5f + 1.2f
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (oldw == 0 && oldh == 0) initEntities(seedText)
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        running = true
        startNanos = System.nanoTime()
        choreographer.postFrameCallback(this)
    }

    override fun onDetachedFromWindow() {
        running = false
        choreographer.removeFrameCallback(this)
        super.onDetachedFromWindow()
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (running) {
            if (lastRenderedFrameNanos == 0L ||
                frameTimeNanos - lastRenderedFrameNanos >= minimumFrameIntervalNanos
            ) {
                lastRenderedFrameNanos = frameTimeNanos
                invalidate()
            }
            choreographer.postFrameCallback(this)
        }
    }

    private fun hsl(hue: Float, sat: Float, light: Float, alpha: Int): Int {
        val h = ((hue % 360f + 360f) % 360f) / 360f
        val s = sat.coerceIn(0f, 1f)
        val l = light.coerceIn(0f, 1f)
        if (s == 0f) {
            val v = (l * 255).toInt()
            return Color.argb(alpha, v, v, v)
        }
        val q = if (l < .5f) l * (1 + s) else l + s - l * s
        val p = 2 * l - q
        fun rgb(t0: Float): Float {
            var t = t0
            if (t < 0) t += 1f
            if (t > 1) t -= 1f
            return when {
                t < 1f / 6f -> p + (q - p) * 6 * t
                t < .5f -> q
                t < 2f / 3f -> p + (q - p) * (2f / 3f - t) * 6
                else -> p
            }
        }
        return Color.argb(
            alpha,
            (rgb(h + 1f / 3f) * 255).toInt(),
            (rgb(h) * 255).toInt(),
            (rgb(h - 1f / 3f) * 255).toInt()
        )
    }

    /*
     * Cache an alpha mask for border mode. The rounded rectangle is a fully
     * clear center; opacity feathers outward into the perimeter band. Masking
     * after drawing prevents radial gradients from bleeding into the center.
     */
    private fun createBorderMask(w: Int, h: Int): Bitmap {
        val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val pixels = IntArray(w * h)
        val inset = (borderWidthDp * density)
            .coerceIn(8f * density, min(w, h) * 0.35f)
        val halfW = (w - 2f * inset) * 0.5f
        val halfH = (h - 2f * inset) * 0.5f
        val radius = min(inset * 0.9f, min(halfW, halfH))
        val cx = w * 0.5f
        val cy = h * 0.5f
        val feather = maxOf(inset * 0.9f, 16f * density)
        val maxAlpha = borderOpacity.coerceIn(0f, 1f)

        for (y in 0 until h) {
            val qy = abs((y + 0.5f) - cy) - (halfH - radius)
            for (x in 0 until w) {
                val qx = abs((x + 0.5f) - cx) - (halfW - radius)
                val outsideX = maxOf(qx, 0f)
                val outsideY = maxOf(qy, 0f)
                val outsideDistance = sqrt(outsideX * outsideX + outsideY * outsideY)
                val insideDistance = min(maxOf(qx, qy), 0f)
                val signedDistance = outsideDistance + insideDistance - radius
                val t = (signedDistance / feather).coerceIn(0f, 1f)
                val smooth = t * t * (3f - 2f * t)
                val alpha = (255f * maxAlpha * smooth).toInt().coerceIn(0, 255)
                val finalAlpha = if (inverseBorderMask) 255 - alpha else alpha
                pixels[y * w + x] = Color.argb(finalAlpha, 255, 255, 255)
            }
        }
        bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
        return bitmap
    }

    private fun ensureBorderMask() {
        if (borderMask == null || borderMaskWidth != width || borderMaskHeight != height) {
            borderMask?.recycle()
            borderMask = createBorderMask(width, height)
            borderMaskWidth = width
            borderMaskHeight = height
        }
    }

    private fun drawEntity(c: Canvas, e: WaveEntity, pulse: Float) {
        val base = if (e.isShadow) .35f + pulse * .15f else .42f + pulse * .20f
        val a = (base * 255f).toInt().coerceIn(0, 255)

        val center: Int
        val gradientEdge: Int
        if (e.isShadow) {
            val v = if (darkMode) 210 else 110
            center = Color.argb(a, v, v, v - 5)
            gradientEdge = Color.TRANSPARENT
        } else if (darkMode) {
            center = hsl(e.hue, .65f, .48f, a)
            gradientEdge = hsl(e.hue, .55f, .25f, 0)
        } else {
            center = hsl(e.hue, .55f, .72f, a)
            gradientEdge = hsl(e.hue, .45f, .80f, 0)
        }

        paint.shader = RadialGradient(
            e.x, e.y, e.radius,
            center, gradientEdge,
            Shader.TileMode.CLAMP
        )
        c.drawCircle(e.x, e.y, e.radius, paint)
        paint.shader = null
    }

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        if (width <= 0 || height <= 0) return

        val elapsed = if (startNanos == 0L) 0.0 else
            (System.nanoTime() - startNanos) / 1_000_000_000.0
        // Keep the visual field steady by default. Rhythmic pulsing is explicitly opt-in.
        val pulse = if (flashingEnabled) {
            ((sin(2 * Math.PI * targetHz * elapsed) + 1) * .5).toFloat()
        } else 0.5f

        if (isFullOverlay) {
            paint.color = if (darkMode) Color.rgb(27, 27, 28) else Color.rgb(228, 228, 227)
            paint.alpha = (255 * fullOpacity.coerceIn(0f, 1f)).toInt()
            paint.shader = null
            c.drawRect(0f, 0f, width.toFloat(), height.toFloat(), paint)
        }

        val borderLayer = if (!isFullOverlay) {
            c.saveLayer(0f, 0f, width.toFloat(), height.toFloat(), null)
        } else -1

        entities.forEach { e ->
            e.angleX += e.speedX
            e.angleY += e.speedY
            e.x += sin(e.angleX.toDouble()).toFloat() * e.amp + e.vx
            e.y += cos(e.angleY.toDouble()).toFloat() * e.amp + e.vy
            e.hue += .1f

            if (e.x < -e.radius) e.x = width + e.radius
            if (e.x > width + e.radius) e.x = -e.radius
            if (e.y < -e.radius) e.y = height + e.radius
            if (e.y > height + e.radius) e.y = -e.radius

            drawEntity(c, e, pulse)
        }

        if (!isFullOverlay) {
            ensureBorderMask()
            c.drawBitmap(borderMask!!, 0f, 0f, borderMaskPaint)
            c.restoreToCount(borderLayer)
        }
        paint.alpha = 255
    }
}
