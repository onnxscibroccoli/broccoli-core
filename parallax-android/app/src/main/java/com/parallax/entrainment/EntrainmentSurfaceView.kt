package com.parallax.entrainment

import android.content.Context
import android.graphics.*
import android.view.SurfaceHolder
import android.view.SurfaceView
import kotlin.math.sin

class EntrainmentSurfaceView(
    context: Context,
    private val isFullOverlay: Boolean,
    private val targetHz: Float,
    seedStr: String
) : SurfaceView(context), SurfaceHolder.Callback, Runnable {

    private var renderThread: Thread? = null
    @Volatile private var running = false
    private val surfaceHolder = holder
    private var state = seedStr.hashCode().toLong() and 0xffffffffL
    private val border = 48f
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    init {
        setZOrderOnTop(true)
        surfaceHolder.setFormat(PixelFormat.TRANSLUCENT)
        surfaceHolder.addCallback(this)
    }

    private fun nextRandom(): Float {
        state = (state + 0x6D2B79F5L) and 0xffffffffL
        var z = state
        z = (z xor (z ushr 13)) * 0x5bd1e995L and 0xffffffffL
        z = z xor (z ushr 15)
        return (z and 0xffffffffL).toFloat() / 4294967296f
    }

    override fun run() {
        val start = System.nanoTime()
        while (running) {
            if (!surfaceHolder.surface.isValid) {
                Thread.sleep(8)
                continue
            }
            val canvas = surfaceHolder.lockCanvas() ?: continue
            try {
                val elapsed = (System.nanoTime() - start) / 1_000_000_000.0
                val pulse = ((sin(2.0 * Math.PI * targetHz * elapsed) + 1.0) / 2.0).toFloat()
                canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)

                if (!isFullOverlay) canvas.save()
                if (!isFullOverlay) {
                    canvas.clipOutRect(
                        border, border,
                        width.toFloat() - border,
                        height.toFloat() - border
                    )
                }

                val wobbleX = (nextRandom() - 0.5f) * width * 0.03f
                val wobbleY = (nextRandom() - 0.5f) * height * 0.03f
                val alpha = (55 + pulse * 105).toInt().coerceIn(0, 255)
                paint.shader = RadialGradient(
                    width / 2f + wobbleX,
                    height / 2f + wobbleY,
                    maxOf(width, height) * 0.8f,
                    intArrayOf(Color.argb(alpha, 120, 140, 255), Color.TRANSPARENT),
                    floatArrayOf(0f, 1f),
                    Shader.TileMode.CLAMP
                )
                canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), paint)
                paint.shader = null

                if (!isFullOverlay) canvas.restore()
            } finally {
                surfaceHolder.unlockCanvasAndPost(canvas)
            }
            Thread.sleep(16)
        }
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        running = true
        renderThread = Thread(this, "ParallaxRender").also { it.start() }
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        running = false
        renderThread?.interrupt()
        renderThread?.join(1000)
        renderThread = null
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) = Unit
}
