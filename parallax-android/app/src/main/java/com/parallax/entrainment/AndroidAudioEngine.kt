package com.parallax.entrainment
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlin.concurrent.thread
import kotlin.math.PI
import kotlin.math.sin

class AndroidAudioEngine(private val targetHz:Float,private val seedStr:String,private val volume:Float=.12f){
    private var track:AudioTrack?=null;@Volatile private var playing=false;private val sampleRate=44100;private val carrier=210.0
    fun start(){
        val min=AudioTrack.getMinBufferSize(sampleRate,AudioFormat.CHANNEL_OUT_STEREO,AudioFormat.ENCODING_PCM_FLOAT);if(min<=0)return
        track=AudioTrack.Builder().setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
            .setAudioFormat(AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_FLOAT).setSampleRate(sampleRate).setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
            .setBufferSizeInBytes(maxOf(min,4096)).setTransferMode(AudioTrack.MODE_STREAM).build()
        playing=true;track?.play()
        thread(name="ParallaxAudio"){val frames=1024;val buf=FloatArray(frames*2);var sample=0L
            val off=((seedStr.hashCode() and 0x7fffffff)%3000)/100.0-15.0;val left=carrier+off;val right=left+targetHz;val gain=volume.coerceIn(0f,1f)
            while(playing){for(i in 0 until frames){val t=sample.toDouble()/sampleRate;buf[i*2]=(sin(2*PI*left*t)*gain).toFloat();buf[i*2+1]=(sin(2*PI*right*t)*gain).toFloat();sample++};track?.write(buf,0,buf.size,AudioTrack.WRITE_BLOCKING)}
        }
    }
    fun stop(){playing=false;runCatching{track?.stop()};track?.release();track=null}
}