package ai.broccoli.a11y

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class A11yCommandReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val svc = BroccoliA11yService.inst ?: run {
            Log.w("BroccoliA11y", "service not running")
            return
        }
        val op = intent.getStringExtra("op") ?: return
        val pkg = intent.getStringExtra("target_pkg") ?: "ai.x.grok"
        val text = intent.getStringExtra("text") ?: ""
        val ok = when (op) {
            "click_send" -> svc.clickSend(pkg)
            "click_text" -> svc.clickText(text, pkg)
            "set_text_focused" -> svc.setTextFocused(text, pkg)
            else -> false
        }
        Log.i("BroccoliA11y", "op=$op ok=$ok")
    }
}
