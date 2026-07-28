package ai.broccoli.a11y

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityNodeInfo

class BroccoliA11yService : AccessibilityService() {
    companion object {
        @JvmStatic var inst: BroccoliA11yService? = null
    }
    override fun onServiceConnected() {
        super.onServiceConnected()
        inst = this
    }
    override fun onDestroy() {
        inst = null
        super.onDestroy()
    }
    override fun onAccessibilityEvent(event: android.view.accessibility.AccessibilityEvent?) {}
    override fun onInterrupt() {}

    fun clickSend(pkg: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val nodes = mutableListOf<AccessibilityNodeInfo>()
        findClickable(root, nodes)
        for (n in nodes) {
            val t = (n.text?.toString() ?: "") + (n.contentDescription?.toString() ?: "")
            val rid = n.viewIdResourceName ?: ""
            if (t.contains("send", true) || rid.contains("send", true)) {
                if (n.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            }
        }
        // right-side icon near bottom EditText
        val edits = root.findAccessibilityNodeInfosByViewId("android:id/edit")
        if (edits.isNullOrEmpty()) {
            for (n in nodes) if (n.className?.contains("EditText") == true) {
                return clickSiblingSend(n)
            }
        }
        return nodes.lastOrNull()?.performAction(AccessibilityNodeInfo.ACTION_CLICK) == true
    }

    private fun clickSiblingSend(edit: AccessibilityNodeInfo): Boolean {
        val p = edit.parent ?: return false
        for (i in 0 until p.childCount) {
            val c = p.getChild(i) ?: continue
            if (c != edit && c.isClickable) {
                if (c.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            }
        }
        return false
    }

    fun setTextFocused(text: String, pkg: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return false
        val args = android.os.Bundle()
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        return focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    fun clickText(text: String, pkg: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val list = root.findAccessibilityNodeInfosByText(text)
        for (n in list) if (n.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
        return false
    }

    private fun findClickable(n: AccessibilityNodeInfo, out: MutableList<AccessibilityNodeInfo>) {
        if (n.isClickable) out.add(n)
        for (i in 0 until n.childCount) {
            n.getChild(i)?.let { findClickable(it, out) }
        }
    }
}
