
#!/usr/bin/env python3
import argparse, json, re, sys
from pathlib import Path
from xml.etree import ElementTree as ET
B = Path.home() / "broccoli"
XML, CTX, ENV = B/"reports/ui_dump.xml", B/"reports/wire_context.json", B/"meta/wire_coords.env"
def load_pkg():
    if ENV.is_file():
        for line in ENV.read_text(errors="replace").splitlines():
            if line.startswith("GROK_PKG="): return line.split("=",1)[1].strip()
    return "ai.x.grok"
def center(bounds):
    if isinstance(bounds, list) and len(bounds)==4:
        x1,y1,x2,y2=bounds; return (x1+x2)//2,(y1+y2)//2
    m=re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", str(bounds))
    if m: a=list(map(int,m.groups())); return (a[0]+a[2])//2,(a[1]+a[3])//2
    return None
def from_json():
    if not CTX.is_file(): return None,None
    j=json.loads(CTX.read_text()); s,jc=j.get("send"),j.get("composer")
    return (center(s["bounds"]) if s and s.get("bounds") else None,
            center(jc["bounds"]) if jc and jc.get("bounds") else None)
def from_xml():
    if not XML.is_file() or XML.stat().st_size<300: return None,None
    root=ET.fromstring(XML.read_text(errors="replace"))
    sxy=cxy=None
    for n in root.iter():
        lab=(n.attrib.get("content-desc") or n.attrib.get("text") or "").strip()
        b=n.attrib.get("bounds")
        if re.search(r"(?i)send message|^send$", lab): sxy=center(b) or sxy
        if re.search(r"(?i)message grok|composer", lab): cxy=center(b) or cxy
    return sxy,cxy
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--emit-send", action="store_true")
    ap.add_argument("--msg", default=""); a=ap.parse_args()
    pkg=load_pkg(); sxy,cxy=from_json()
    if not sxy: sxy,cxy2=from_xml(); cxy=cxy or cxy2
    lines=["export PATH=\"$HOME/bin:$PATH\"",
           f"rish -c 'am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {pkg}'",
           "sleep 1.2","brocc dump"]
    if a.msg:
        esc=a.msg.replace("'","'\"'\"'")
        lines+=["brocc send '"+esc+"'","sleep 0.6","brocc dump"]
    if a.emit_send and sxy:
        x,y=sxy; lines.append(f"rish -c 'input tap {x} {y}'")
    elif a.emit_send:
        print("# FAIL no Send bounds — foreground Grok chat then brocc dump"); return 1
    print("\n".join(lines)); return 0
if __name__=="__main__": sys.exit(main())
