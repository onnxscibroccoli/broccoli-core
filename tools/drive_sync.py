#!/usr/bin/env python3

import os
import shutil
import subprocess
import time
import json
from pathlib import Path

REPO = Path.home() / "broccoli-core"
STAGE = REPO / ".sync_stage"
STATE = REPO / "tools/sync_state.json"
FAIL = REPO / "tools/sync_failures.txt"

REMOTE = "gdrive:"
REMOTE_PATH = "BroccoliWorkspaceBackup"

RESERVE_MB = 1000
BATCH_FILES = 20
BATCH_MB = 150

state = {
    "copied":0,
    "skipped":0,
    "failed":0,
    "batch":0,
    "bytes":0,
    "start":time.time()
}

def run(cmd):
    return subprocess.run(cmd,text=True,capture_output=True)

def git(*args):
    return run(["git",*args])

def free_mb():
    return shutil.disk_usage(str(REPO)).free//1024//1024

def save():
    STATE.write_text(json.dumps(state,indent=2))

def log_fail(msg):
    with open(FAIL,"a") as f:
        f.write(msg+"\n")

print()
print("=== Preparing Git ===")

git("config","user.name","Broccoli Core")
git("config","user.email","broccoli@example.invalid")

git("remote","set-url","origin","git@github.com:onnxscibroccoli/broccoli-core.git")
git("fetch","origin")

print("=== Reading GitHub inventory ===")

tracked = set(
    git("ls-files").stdout.splitlines()
)

print("Tracked:",len(tracked))

print("=== Reading Drive inventory ===")

ls = run([
    "rclone",
    "lsjson",
    "-R",
    f"{REMOTE}{REMOTE_PATH}"
])

if ls.returncode:
    print(ls.stderr)
    raise SystemExit(1)

files = json.loads(ls.stdout)

total = len(files)

remaining = total

batch_files=[]
batch_bytes=0

last=time.time()

for f in files:

    if f.get("IsDir"):
        continue

    path=f["Path"]

    remaining-=1

    if path in tracked:
        state["skipped"]+=1
        continue

    if free_mb()<RESERVE_MB:
        print("\nSTOPPED: storage reserve reached.")
        break

    src=f"{REMOTE}{REMOTE_PATH}/{path}"
    dst=STAGE/path

    dst.parent.mkdir(parents=True,exist_ok=True)

    print("[copy]",path)

    rc=run([
        "rclone",
        "copyto",
        src,
        str(dst)
    ])

    if rc.returncode:
        state["failed"]+=1
        log_fail(path)
        continue

    final=REPO/path
    final.parent.mkdir(parents=True,exist_ok=True)

    shutil.move(dst,final)

    size=f.get("Size",0)

    state["copied"]+=1
    state["bytes"]+=size

    batch_files.append(path)
    batch_bytes+=size

    elapsed=max(time.time()-state["start"],1)

    speed=state["bytes"]/elapsed

    eta="calculating"

    if speed>0:
        remain_bytes=max(0,sum(x.get("Size",0) for x in files if not x.get("IsDir"))-state["bytes"])
        eta_sec=int(remain_bytes/speed)
        eta=time.strftime("%H:%M:%S",time.gmtime(eta_sec))

    percent=(state["copied"]+state["skipped"])/max(total,1)*100

    print(
        f"[progress] {state['copied']+state['skipped']}/{total} "
        f"({percent:.1f}%) "
        f"copied={state['copied']} "
        f"skipped={state['skipped']} "
        f"failed={state['failed']}"
    )

    print(
        f"[speed] {(speed/1024/1024):.2f} MB/s   "
        f"[eta] {eta}   "
        f"[space] {free_mb()} MB"
    )

    if len(batch_files)>=BATCH_FILES or batch_bytes>=BATCH_MB*1024*1024:

        git("add","-A")

        msg="Drive sync "+time.strftime("%Y-%m-%d %H:%M:%S")

        commit=git("commit","-m",msg)

        if commit.returncode==0:

            push=git("push","origin","main")

            if push.returncode==0:
                print("[push] success")
            else:
                print(push.stderr)

        batch_files=[]
        batch_bytes=0

    save()

if batch_files:

    git("add","-A")
    git("commit","-m","Drive sync "+time.strftime("%Y-%m-%d %H:%M:%S"))
    git("push","origin","main")

print()
print("============== COMPLETE ==============")
print("Copied   :",state["copied"])
print("Skipped  :",state["skipped"])
print("Failed   :",state["failed"])
print("Free MB  :",free_mb())

last=git("rev-parse","HEAD")
print("Commit   :",last.stdout.strip())

if FAIL.exists():
    print("Failures :",FAIL)
