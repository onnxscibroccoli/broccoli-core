#!/usr/bin/env python3
import argparse,gzip,hashlib,json,sqlite3,datetime,os
from pathlib import Path
BRO=Path.home()/"broccoli"
ARCH=BRO/"archive/conversations"
IDX=BRO/"archive/index.sqlite"
PULL=Path(os.environ.get("BROCCOLI_PULL_DIR","/sdcard/Broccoli/pull"))
INB=BRO/"inbox/grok_reply.txt"
def db():
    ARCH.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(IDX)
    c.execute("CREATE TABLE IF NOT EXISTS conv(id TEXT PRIMARY KEY,ts TEXT,src TEXT,path TEXT,sha TEXT,bytes INT,prev TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS lookup(kw TEXT,cid TEXT)")
    c.commit();return c
def ingest():
    c=db();n=0;items=[]
    if INB.exists() and INB.stat().st_size: items.append(("inbox",INB.read_text(encoding="utf-8",errors="replace")))
    if PULL.exists():
        for b in sorted(PULL.glob("bundle_*"),key=lambda p:p.stat().st_mtime,reverse=True)[:15]:
            try: t=b.read_text(encoding="utf-8",errors="replace")
            except: continue
            if t.strip(): items.append((b.name,t))
    for src,t in items:
        sha=hashlib.sha256(t.encode("utf-8",errors="replace")).hexdigest()
        if c.execute("SELECT 1 FROM conv WHERE sha=?",(sha,)).fetchone(): continue
        cid=sha[:16];ts=datetime.datetime.now().isoformat()
        out=ARCH/f"{ts.replace(':','-')}_{cid}.jsonl.gz"
        with gzip.open(out,"wt",encoding="utf-8") as f: f.write(json.dumps({"ts":ts,"src":src,"text":t},ensure_ascii=False)+"\n")
        prev=t[:500]
        c.execute("INSERT INTO conv VALUES(?,?,?,?,?,?,?)",(cid,ts,src,str(out),sha,len(t.encode()),prev))
        for w in set(prev.lower().split()):
            if len(w)>3: c.execute("INSERT INTO lookup VALUES(?,?)",(w,cid))
        n+=1
    c.commit();c.close();print("INGEST_OK",n)
def lookup(k,limit=5):
    c=db()
    rows=c.execute("SELECT c.prev,c.path,c.ts FROM lookup l JOIN conv c ON l.cid=c.id WHERE l.kw=? LIMIT ?",(k.lower(),limit)).fetchall()
    c.close()
    for r in rows: print("---",r[2],r[1]);print(r[0][:800])
    print("LOOKUP_OK",len(rows))
def maintain(keep=5):
    if PULL.exists():
        for old in sorted(PULL.glob("bundle_*"),key=lambda p:p.stat().st_mtime,reverse=True)[keep:]:
            old.unlink(missing_ok=True)
    print("MAINTAIN_OK")
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--ingest",action="store_true")
    ap.add_argument("--lookup")
    ap.add_argument("--maintain",action="store_true")
    o=ap.parse_args()
    if o.ingest: ingest()
    elif o.lookup: lookup(o.lookup)
    elif o.maintain: maintain()
    else: ingest();maintain()
