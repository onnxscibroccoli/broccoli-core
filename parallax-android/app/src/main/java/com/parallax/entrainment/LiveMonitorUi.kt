package com.parallax.entrainment

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.widget.Toast

/** Visible, explicit microphone authorization shared by both settings screens. */
object LiveMonitorUi {
    const val REQUEST_MIC = 77

    fun confirmStart(activity: Activity) {
        if (!PlaybackReferenceBus.sessionPlaying || !PlaybackReferenceBus.builtInSpeaker) {
            message(activity, "Start a Parallax audio session on the built-in speaker first. " +
                "Phone microphone cannot verify audio routed to headphones or Bluetooth.")
            return
        }
        if (AcousticBus.calibrating || AcousticBus.polling) {
            message(activity, "Stop room calibration before continuous audio comparison.")
            return
        }
        AlertDialog.Builder(activity)
            .setTitle("Continuously compare microphone and Parallax audio?")
            .setMessage("This explicitly enables a microphone foreground service while the " +
                "audible Parallax session is running. It compares the post-EQ speaker signal " +
                "against microphone spectral energy about three times per second, without " +
                "saving recordings. Stop from this screen or the ongoing notification. " +
                "Headphones and Bluetooth cannot be evaluated through the phone microphone.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Enable microphone") { _, _ ->
                if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
                    PackageManager.PERMISSION_GRANTED)
                    activity.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQUEST_MIC)
                else launch(activity)
            }.show()
    }

    fun launch(activity: Activity) {
        if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED) {
            message(activity, "Microphone permission not granted.")
            return
        }
        if (!PlaybackReferenceBus.sessionPlaying || !PlaybackReferenceBus.builtInSpeaker ||
            AcousticBus.calibrating || AcousticBus.polling) {
            message(activity, "Built-in speaker audio must be active, with calibration off.")
            return
        }
        try {
            val intent = Intent(activity, LiveAudioMonitorService::class.java)
            if (Build.VERSION.SDK_INT >= 26) activity.startForegroundService(intent)
            else activity.startService(intent)
        } catch (e: RuntimeException) {
            message(activity, "Android blocked microphone startup: " + (e.message ?: "unavailable"))
        }
    }

    fun stop(activity: Activity) {
        activity.stopService(Intent(activity, LiveAudioMonitorService::class.java))
    }

    fun onPermissionResult(activity: Activity, code: Int, results: IntArray): Boolean {
        if (code != REQUEST_MIC) return false
        if (results.firstOrNull() == PackageManager.PERMISSION_GRANTED) launch(activity)
        else message(activity, "Microphone permission denied; playback continues without comparison.")
        return true
    }

    private fun message(activity: Activity, text: String) {
        PlaybackReferenceBus.status = text
        Toast.makeText(activity, text, Toast.LENGTH_LONG).show()
    }
}
