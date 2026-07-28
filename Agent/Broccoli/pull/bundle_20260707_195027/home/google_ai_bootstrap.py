#!/usr/bin/env python3
import re,sys,os,time,subprocess,shutil,json
PKG="com.google.android.googlequicksearchbox"
SEARCH=PKG+"/.SearchActivity"
DUMP="/data/local/tmp/broccoli_gai.xml"
LOCAL=os.path.expanduser("~/google_ai_ui_dump.xml")
URL="https://www.google.com/ai"
def log(*a): print(*a,flush=True)
def rish_exe(): return shutil.which("rish") or "/data/data/com.termux/files/usr/bin/rish"
def rish(c,t=90): return subprocess.run([rish_exe(),"-c",c],capture_output=True,text=True,timeout=t)
def focus():
 o,e=rish("dumpsys window | grep mCurrentFocus | head -1",12); f=(o.stdout+e.stderr).lower()
 return (PKG in f or "googlequicksearchbox" in f) and "termux" not in f, f.strip()[:90]
def launch():
 log("launch_google"); rish("am start -W -n "+SEARCH,45); time.sleep(2.5)
 ok,f=focus()
 if not ok: rish('am start -a android.intent.action.VIEW -d "'+URL+'" -p '+PKG,45); time.sleep(3); ok,f=focus()
 log("focus",f); return ok
def dump():
 rish("uiautomator dump "+DUMP,50); time.sleep(0.7)
 with open(LOCAL,"wb") as o: subprocess.run([rish_exe(),"-c","cat "+DUMP],stdout=o,timeout=90)
 raw=open(LOCAL,"r",errors="replace").read(); i=raw.find("<hierarchy")
 if i<0: return ""
 xml=raw[i:]; e=xml.rfind("</hierarchy>"); xml=xml[:e+12] if e>0 else xml
 open(LOCAL,"w").write(xml); log("dump",len(xml)); return xml
def nodes(xml):
 out=[]
 for part in (xml or "").split("<node ")[1:]:
  ch=part.split("/>",1)[0]; m=re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',ch)
  if not m: continue
  l,t,r,b=map(int,m.groups()); rid=re.search(r'resource-id="([^"]*)"',ch); desc=re.search(r'content-desc="([^"]*)"',ch); txt=re.search(r'text="([^"]*)"',ch)
  out.append({"cx":(l+r)//2,"cy":(t+b)//2,"w":r-l,"txt":(txt.group(1) if txt else ""),"desc":(desc.group(1) if desc else ""),"rid":(rid.group(1) if rid else ""),"click":'clickable="true"' in ch,"cls":(re.search(r'class="([^"]*)"',ch) or [None,""])[1]})
 return out
def tap(x,y,w=""): log("tap",x,y,w); rish("input tap %d %d"%(x,y),12); time.sleep(0.5)
def cal():
 p=os.path.expanduser("~/.google_ai_cal.json"); return json.load(open(p)) if os.path.isfile(p) else {}
def ai_btn(nl):
 for n in nl:
  if "ai mode" in (n["txt"]+" "+n["desc"]).lower(): return n
 return None
def composer(nl):
 c=cal()
 if c.get("composer_cx"): return c["composer_cx"],c["composer_cy"]
 H=max((n["cy"] for n in nl),default=2200)
 for n in nl:
  if "edittext" in n["cls"].lower() and n["cy"]>H*0.55: return n["cx"],n["cy"]
 return 540,int(H*0.9)
def send_xy(nl,cy):
 c=cal()
 if c.get("send_cx"): return c["send_cx"],c["send_cy"]
 for n in nl:
  if n["click"] and n["cx"]>850 and abs(n["cy"]-cy)<250: return n["cx"],n["cy"]
 return 980,cy
def open_ai():
 for _ in range(3):
  nl=nodes(dump()); b=ai_btn(nl)
  if b: tap(b["cx"],b["cy"],"AI Mode"); time.sleep(2); continue
  tap(540,int(max(n["cy"] for n in nl)*0.2),"fallback"); time.sleep(2)
 return True
def reply_text(nl,cy,skip="",want=""):
 cand=[]
 for n in nl:
  t=(n["txt"] or "").strip()
  if len(t)<2 or n["cy"]>=cy-100 or n["cy"]<300: continue
  if skip and skip.lower() in t.lower(): continue
  cand.append((n["cy"],t))
 if not cand: return ""
 if want:
  for _,t in cand:
   if want.lower() in t.lower(): return t
 cand.sort(reverse=True); return cand[0][1]
def done(st,d=""):
 m="GoogleAI %s: %s"%(st,(d or "")[:80]); log("=== BROCCOLI_DONE ===",m)
 open(os.path.expanduser("~/broccoli/LAST_RUN.txt"),"w").write(m+"\n")
 for cmd in (["termux-toast","-s",m[:70]],["termux-vibrate","-d","300"]):
  try: subprocess.run(cmd,timeout=5)
  except: pass
def ask(text,wait=50,want=""):
 if not launch(): raise SystemExit("open Google app on phone first")
 open_ai(); time.sleep(1)
 nl=nodes(dump()); cx,cy=composer(nl); log("composer",cx,cy)
 tap(cx,cy); tap(cx,cy)
 subprocess.run(["termux-clipboard-set"],input=text.encode(),timeout=10); time.sleep(0.3)
 rish("input keyevent 279",12); time.sleep(0.8)
 nl2=nodes(dump()); sx,sy=send_xy(nl2,cy); log("send",sx,sy); tap(sx,sy); tap(sx,sy)
 t0=time.time(); prev=""; stable=0; last=""
 while time.time()-t0<wait:
  time.sleep(1.5); nl3=nodes(dump()); cx3,cy3=composer(nl3); last=reply_text(nl3,cy3,text[:40],want)
  if want and last and want in last: return last
  if last and last==prev: stable+=1
  else: stable=0; prev=last
  if stable>=2: break
 return last
def main():
 if len(sys.argv)<2: log("google-ai-smoke | google-ai-ask TEXT | google-ai-dump"); return
 a=sys.argv[1]
 if a=="google-ai-dump":
  launch(); nl=nodes(dump()); log("ai_btn",ai_btn(nl)); open_ai(); nl2=nodes(dump()); c=composer(nl2); log("composer",c,"send",send_xy(nl2,c[1]))
  return
 if a=="google-ai-smoke":
  r=ask("Reply with only GOOGLE_AI_SMOKE_OK",want="GOOGLE_AI_SMOKE_OK"); ok=r and "GOOGLE_AI_SMOKE_OK" in r
  done("PASS" if ok else "FAIL",r); log("PASS" if ok else "FAIL",repr(r)[:120]); return
 if a=="google-ai-ask":
  p=" ".join(sys.argv[2:]) if len(sys.argv)>2 else sys.stdin.read().strip()
  r=ask(p); ts=time.strftime("%Y%m%d_%H%M%S")
  json.dump({"provider":"google_ai_mode","prompt":p,"reply":r,"ts":ts},open(os.path.expanduser("~/broccoli/runs/google_ai_%s.json"%ts),"w"),indent=2)
  done("OK",r); print(r); return
if __name__=="__main__": main()
