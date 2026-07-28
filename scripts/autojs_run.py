#!/usr/bin/env python3
import os,subprocess,sys,time,json
ROOT=os.path.expanduser("~/broccoli")
SD="/sdcard/broccoli/autojs"
PKG=os.environ.get("AUTOJS_PKG","org.autojs.autojs6")
ACT=os.environ.get("AUTOJS_ACT","org.autojs.autojs.external.open.RunIntentActivity")
def run_js(name,wait_out=None,timeout=90):
    path=f"{SD}/{name}"
    subprocess.run(["am","start","-n",f"{PKG}/{ACT}","-d",f"file://{path}"],capture_output=True,timeout=15)
    t0=time.time()
    while wait_out and time.time()-t0<timeout:
        if os.path.isfile(wait_out) and os.path.getmtime(wait_out)>t0-2: return True
        time.sleep(0.4)
    return not wait_out
if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else "fsm"
    if cmd=="fsm": run_js("grok_button_fsm.js","/sdcard/broccoli/ui/button_state.json",timeout=25); print(open("/sdcard/broccoli/ui/button_state.json").read() if os.path.isfile("/sdcard/broccoli/ui/button_state.json") else "no state")
    elif cmd=="read": run_js("grok_read_chat.js","/sdcard/broccoli/ui/last_capture.txt",timeout=20); print(open("/sdcard/broccoli/ui/last_capture.txt").read()[-500:] if os.path.isfile("/sdcard/broccoli/ui/last_capture.txt") else "no cap")
