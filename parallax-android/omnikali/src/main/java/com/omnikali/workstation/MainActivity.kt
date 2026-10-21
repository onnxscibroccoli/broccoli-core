package com.omnikali.workstation

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.content.Intent
import android.net.Uri
import android.view.ViewGroup
import android.webkit.*
import android.widget.*
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
 private val bg=Color.rgb(12,17,28); private val panel=Color.rgb(23,31,47); private val accent=Color.rgb(104,184,255); private val ink=Color.rgb(235,242,252)
 private lateinit var content: LinearLayout; private lateinit var status: TextView; private lateinit var endpoint: EditText
 private var web: WebView?=null; private var active="Workspaces"
 private val prefs by lazy { getSharedPreferences("omnikali",MODE_PRIVATE) }
 private val ociDesktopUrl="http://129.213.28.18/vnc.html?autoconnect=true&resize=scale&reconnect=true"
 private val ociHost="129.213.28.18"
 override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); window.statusBarColor=bg; window.navigationBarColor=bg; shell(); render() }
 private fun shell() {
  val root=LinearLayout(this).apply { orientation=1; setBackgroundColor(bg); setPadding(dp(14),dp(10),dp(14),dp(8)) }
  root.addView(TextView(this).apply { text="OMNIKALI  /  WORKSTATION"; textSize=17f; setTextColor(accent); typeface=Typeface.DEFAULT_BOLD; setPadding(0,dp(8),0,dp(5)) })
  status=TextView(this).apply { text="OCI WORKSTATION READY • SESSION AUTH NOT VERIFIED"; textSize=11f; setTextColor(Color.LTGRAY); setPadding(0,0,0,dp(10)) }; root.addView(status)
  val nav=LinearLayout(this).apply { orientation=0 }
  listOf("Workspaces","Terminal","Browser","Automation","Settings").forEach { label -> nav.addView(Button(this).apply { text=label; textSize=9f; isAllCaps=false; setTextColor(if(label==active)accent else ink); setBackgroundColor(panel); setOnClickListener { active=label; render() } },LinearLayout.LayoutParams(0,dp(44),1f).apply { setMargins(dp(1),0,dp(1),0) }) }
  root.addView(nav); content=LinearLayout(this).apply { orientation=1; setPadding(0,dp(12),0,0) }
  root.addView(ScrollView(this).apply { isFillViewport=true; addView(content) },LinearLayout.LayoutParams(-1,0,1f)); setContentView(root)
 }
 private fun render() { content.removeAllViews(); web?.destroy(); web=null; when(active) { "Workspaces"->workspaces(); "Terminal"->terminal(); "Browser"->browser(); "Automation"->automation(); else->settings() } }
 private fun workspaces() {
  title("Persistent workspaces")
  body("Open the existing OCI workstation directly. The remote desktop remains on the server when this app is closed.")
  card("OCI WORKSTATION","Oracle Linux XFCE desktop • noVNC • automatic reconnect • adaptive scaling")
  action("Open OCI workstation desktop") { openOciDesktop() }
  action("Open OCI desktop in system browser") { startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(ociDesktopUrl))) }
  card("KALI / LINUX","Persistent Linux desktop, authenticated terminal and remote Playwright browser.")
  card("CLOUD ANDROID","Remote Android guest with browser and UI automation.")
  card("CONTROL PLANE","Helix owns protected lifecycle; Grasshopper defines cross-project contracts.")
  field()
  action("Check HTTPS endpoint"){checkEndpoint()}
  action("Open remote endpoint"){openRemote("")}
  body("The OCI desktop button targets the existing VNC endpoint. It uses HTTP because the current endpoint does not have TLS; do not enter passwords or other secrets on untrusted networks until HTTPS is configured.")
 }
 private fun terminal() { title("Remote terminal"); body("Connect to an authenticated server-side PTY. This app does not execute arbitrary commands on the Android host."); field(); action("Open terminal endpoint"){openRemote("/terminal")} }
 private fun browser() {
  title("Browser sessions")
  body("Embedded web mode is restricted to HTTPS origins, except for the explicitly configured OCI VNC host.")
  action("Open OCI workstation desktop") { openOciDesktop() }
  field()
  action("Open embedded web app"){val u=endpoint.text.toString().trim(); if(valid(u)) loadWeb(u) else toast("Enter a valid HTTPS URL")}
  action("Open system browser"){val u=endpoint.text.toString().trim(); if(valid(u)) startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(u))) else toast("Enter a valid HTTPS URL")}
 }
 private fun automation() { title("Automation broker"); card("PLAYWRIGHT","Run bounded browser jobs beside the remote browser in an isolated profile."); card("HUMAN GATES","Pause for OAuth, CAPTCHA or consent, then resume after human confirmation."); card("EVIDENCE","Collect job state, screenshots and logs. Unverified integrations remain NOT_PROVEN."); field(); action("Open automation console"){openRemote("/automation")} }
 private fun settings() {
  title("Connection settings")
  body("Use an HTTPS control-plane URL for authenticated APIs. The existing OCI noVNC endpoint is a separate, explicitly scoped HTTP exception.")
  field()
  action("Save endpoint"){val u=endpoint.text.toString().trim().trimEnd('/'); if(valid(u)){prefs.edit().putString("endpoint",u).apply();status.text="HTTPS ENDPOINT SAVED • NOT AUTHENTICATED";toast("Saved")}else toast("Valid HTTPS URL required")}
  action("Open OCI workstation desktop") { openOciDesktop() }
  action("Clear endpoint"){prefs.edit().remove("endpoint").apply();endpoint.setText("");toast("Cleared")}
 }
 private fun field() {
  if(::endpoint.isInitialized) (endpoint.parent as? ViewGroup)?.removeView(endpoint)
  endpoint=EditText(this).apply { setSingleLine(true); textSize=14f; setTextColor(ink); setHintTextColor(Color.GRAY); hint="https://control-plane.example"; setBackgroundColor(panel); setPadding(dp(10),dp(8),dp(10),dp(8)); setText(prefs.getString("endpoint","")); inputType=android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI }
  content.addView(endpoint,LinearLayout.LayoutParams(-1,dp(50)).apply { setMargins(0,dp(8),0,dp(8)) })
 }
 private fun openOciDesktop() {
  status.text="OPENING OCI WORKSTATION • HTTP / TLS NOT CONFIGURED"
  loadWeb(ociDesktopUrl)
 }
 private fun openRemote(path:String) { val u=endpoint.text.toString().trim().trimEnd('/'); if(!valid(u)){toast("Enter a valid HTTPS endpoint first");return}; prefs.edit().putString("endpoint",u).apply();loadWeb(u+path) }
 private fun loadWeb(u:String) {
  val isOciDesktop = u == ociDesktopUrl
  if(!valid(u) && !isOciDesktop){toast("Only HTTPS URLs accepted, except the configured OCI desktop");return}
  content.removeAllViews()
  val v=WebView(this); web=v
  v.settings.javaScriptEnabled=true
  v.settings.domStorageEnabled=true
  v.settings.allowFileAccess=false
  v.settings.allowContentAccess=false
  v.settings.javaScriptCanOpenWindowsAutomatically=false
  v.settings.setSupportMultipleWindows(false)
  v.settings.builtInZoomControls=true
  v.settings.displayZoomControls=false
  v.settings.useWideViewPort=true
  v.settings.loadWithOverviewMode=true
  v.webChromeClient=WebChromeClient()
  v.webViewClient=object:WebViewClient(){
   override fun shouldOverrideUrlLoading(view:WebView?,r:WebResourceRequest?):Boolean {
    val uri=r?.url?:return true
    if(uri.scheme=="https") return false
    return !(uri.scheme=="http" && uri.host==ociHost)
   }
   override fun onPageFinished(view:WebView?,url:String?) { super.onPageFinished(view,url); if(url?.startsWith("http://$ociHost/")==true) status.text="OCI DESKTOP CONNECTED TO WEB VIEW • VNC AUTH/HEALTH NOT VERIFIED" }
  }
  val availableHeight=(resources.displayMetrics.heightPixels/resources.displayMetrics.density).toInt()-175
  content.addView(v,LinearLayout.LayoutParams(-1,dp(availableHeight.coerceAtLeast(360))))
  v.loadUrl(u)
 }
 private fun checkEndpoint() { val u=endpoint.text.toString().trim();if(!valid(u)){toast("Enter valid HTTPS endpoint");return};status.text="CHECKING HTTPS ENDPOINT";thread { val result=try { val c=URL(u).openConnection() as HttpURLConnection;c.connectTimeout=5000;c.readTimeout=5000;c.requestMethod="HEAD";val code=c.responseCode;c.disconnect();"HTTP $code" }catch(e:Exception){e.javaClass.simpleName};runOnUiThread{status.text="ENDPOINT CHECK • $result"} } }
 private fun valid(s:String):Boolean=try { val u=Uri.parse(s);u.scheme=="https"&&!u.host.isNullOrBlank() }catch(_:Exception){false}
 private fun title(s:String){content.addView(TextView(this).apply{text=s;textSize=23f;typeface=Typeface.DEFAULT_BOLD;setTextColor(ink);setPadding(0,dp(4),0,dp(10))})}
 private fun body(s:String){content.addView(TextView(this).apply{text=s;textSize=14f;setTextColor(Color.rgb(180,194,213));setPadding(0,dp(4),0,dp(8))})}
 private fun card(h:String,d:String){val box=LinearLayout(this).apply{orientation=1;setBackgroundColor(panel);setPadding(dp(12),dp(10),dp(12),dp(10))};box.addView(TextView(this).apply{text=h;textSize=12f;setTextColor(accent);typeface=Typeface.DEFAULT_BOLD});box.addView(TextView(this).apply{text=d;textSize=14f;setTextColor(ink);setPadding(0,dp(5),0,0)});content.addView(box,LinearLayout.LayoutParams(-1,-2).apply{setMargins(0,dp(4),0,dp(4))})}
 private fun action(s:String,f:()->Unit){content.addView(Button(this).apply{text=s;isAllCaps=false;setTextColor(ink);setBackgroundColor(Color.rgb(39,68,98));setOnClickListener{f()}},LinearLayout.LayoutParams(-1,dp(46)).apply{setMargins(0,dp(3),0,dp(3))})}
 private fun toast(s:String)=Toast.makeText(this,s,Toast.LENGTH_SHORT).show()
 private fun dp(v:Int)=(v*resources.displayMetrics.density).toInt()
 override fun onBackPressed() { val current=web; if(current!=null && current.canGoBack()) current.goBack() else if(current!=null) { web?.destroy(); web=null; render() } else super.onBackPressed() }
 override fun onDestroy(){web?.destroy();web=null;super.onDestroy()}
}
