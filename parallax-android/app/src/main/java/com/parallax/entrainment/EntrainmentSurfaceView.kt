package com.parallax.entrainment

import android.content.Context
import android.content.res.Configuration
import android.graphics.*
import android.view.Choreographer
import android.view.View
import kotlin.math.cos
import kotlin.math.sin

class EntrainmentSurfaceView(
    context: Context,
    private val isFullOverlay: Boolean,
    private val targetHz: Float,
    seedStr: String,
    private val fullOpacity: Float = 1f,
    private val borderWidthDp: Float = 72f,
    private val borderOpacity: Float = 0.75f
) : View(context), Choreographer.FrameCallback {
    private data class WaveEntity(
        val isShadow: Boolean,
        var x: Float = 0f, var y: Float = 0f, var vx: Float = 0f, var vy: Float = 0f,
        var radius: Float = 0f, var hue: Float = 0f, var angleX: Float = 0f, var angleY: Float = 0f,
        var speedX: Float = 0f, var speedY: Float = 0f, var amp: Float = 0f
    )
    private class Mulberry32(seed: Int) {
        private var a = seed
        private fun imul(x: Int, y: Int) = ((x.toLong()*y.toLong()) and 0xffffffffL).toInt()
        fun nextFloat(): Float {
            a += 0x6D2B79F5; var t=a
            t=imul(t xor (t ushr 15),t or 1); t=t xor (t+imul(t xor (t ushr 7),t or 61))
            return ((t xor (t ushr 14)).toUInt().toLong()/4294967296.0).toFloat()
        }
    }
    private val choreographer=Choreographer.getInstance()
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
    private val entities=ArrayList<WaveEntity>(8)
    private var running=false
    private var startNanos=0L
    private var seedText=seedStr
    private val density=resources.displayMetrics.density
    private val darkMode get()=(resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK)==Configuration.UI_MODE_NIGHT_YES

    init { setLayerType(View.LAYER_TYPE_HARDWARE,null); initEntities(seedText) }

    private fun hashSeedStr(str:String):Int { var h=0; for(c in str) h=31*h+c.code; return h }
    private fun initEntities(seed:String) {
        seedText=seed; val r=Mulberry32(hashSeedStr(seed)); entities.clear()
        repeat(5){entities+=WaveEntity(false).also{reset(it,r)}}; repeat(3){entities+=WaveEntity(true).also{reset(it,r)}}
    }
    private fun reset(e:WaveEntity,r:Mulberry32) {
        val m=maxOf(width,height,1).toFloat()
        e.x=r.nextFloat()*width.coerceAtLeast(1); e.y=r.nextFloat()*height.coerceAtLeast(1)
        e.vx=(r.nextFloat()-.5f)*.6f; e.vy=(r.nextFloat()-.5f)*.6f
        e.radius=(r.nextFloat()*.3f+.3f)*m; e.hue=r.nextFloat()*360f
        e.angleX=r.nextFloat()*(Math.PI*2).toFloat(); e.angleY=r.nextFloat()*(Math.PI*2).toFloat()
        e.speedX=r.nextFloat()*.003f+.0015f; e.speedY=r.nextFloat()*.003f+.0015f; e.amp=r.nextFloat()*1.5f+1.2f
    }
    override fun onSizeChanged(w:Int,h:Int,oldw:Int,oldh:Int){super.onSizeChanged(w,h,oldw,oldh);if(oldw==0&&oldh==0)initEntities(seedText)}
    override fun onAttachedToWindow(){super.onAttachedToWindow();running=true;startNanos=System.nanoTime();choreographer.postFrameCallback(this)}
    override fun onDetachedFromWindow(){running=false;choreographer.removeFrameCallback(this);super.onDetachedFromWindow()}
    override fun doFrame(frameTimeNanos:Long){if(running){invalidate();choreographer.postFrameCallback(this)}}

    private fun hsl(hue:Float,sat:Float,light:Float,alpha:Int):Int {
        val h=((hue%360f+360f)%360f)/360f; val s=sat.coerceIn(0f,1f); val l=light.coerceIn(0f,1f)
        if(s==0f){val v=(l*255).toInt();return Color.argb(alpha,v,v,v)}
        val q=if(l<.5f)l*(1+s) else l+s-l*s; val p=2*l-q
        fun rgb(t0:Float):Float{var t=t0;if(t<0)t+=1f;if(t>1)t-=1f;return when{t<1f/6f->p+(q-p)*6*t;t<.5f->q;t<2f/3f->p+(q-p)*(2f/3f-t)*6;else->p}}
        return Color.argb(alpha,(rgb(h+1f/3f)*255).toInt(),(rgb(h)*255).toInt(),(rgb(h-1f/3f)*255).toInt())
    }
    private fun edgeFade(e:WaveEntity):Float {
        if(isFullOverlay)return fullOpacity.coerceIn(0f,1f)
        val b=borderWidthDp*density; val d=minOf(e.x,e.y,width-e.x,height-e.y)
        if(d>b+e.radius)return 0f
        val feather=(e.radius*.75f).coerceAtLeast(8f)
        return ((-(d-b))/feather).coerceIn(0f,1f)*borderOpacity.coerceIn(0f,1f)
    }
    private fun drawEntity(c:Canvas,e:WaveEntity,pulse:Float){
        val fade=edgeFade(e);if(fade<=0)return
        val base=if(e.isShadow).35f+pulse*.15f else .42f+pulse*.20f
        val a=(base*fade*255).toInt().coerceIn(0,255)
        val center:Int;val edge:Int
        if(e.isShadow){val v=if(darkMode)210 else 110;center=Color.argb(a,v,v,v-5);edge=Color.TRANSPARENT}
        else if(darkMode){center=hsl(e.hue,.65f,.48f,a);edge=hsl(e.hue,.55f,.25f,0)}
        else{center=hsl(e.hue,.55f,.72f,a);edge=hsl(e.hue,.45f,.80f,0)}
        paint.shader=RadialGradient(e.x,e.y,e.radius,center,edge,Shader.TileMode.CLAMP)
        c.drawCircle(e.x,e.y,e.radius,paint);paint.shader=null
    }
    override fun onDraw(c:Canvas){
        super.onDraw(c);val elapsed=if(startNanos==0L)0.0 else (System.nanoTime()-startNanos)/1_000_000_000.0
        if(width<=0||height<=0)return
        val pulse=((sin(2*Math.PI*targetHz*elapsed)+1)*.5).toFloat()
        if(isFullOverlay){paint.color=if(darkMode)Color.rgb(27,27,28)else Color.rgb(228,228,227);paint.alpha=(255*fullOpacity.coerceIn(0f,1f)).toInt();c.drawRect(0f,0f,width.toFloat(),height.toFloat(),paint)}
        entities.forEach{e->
            e.angleX+=e.speedX;e.angleY+=e.speedY;e.x+=sin(e.angleX.toDouble()).toFloat()*e.amp+e.vx;e.y+=cos(e.angleY.toDouble()).toFloat()*e.amp+e.vy;e.hue+=.1f
            if(e.x< -e.radius)e.x=width+e.radius;if(e.x>width+e.radius)e.x=-e.radius;if(e.y< -e.radius)e.y=height+e.radius;if(e.y>height+e.radius)e.y=-e.radius
            drawEntity(c,e,pulse)
        };paint.alpha=255
    }
}