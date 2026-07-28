#!/usr/bin/env python3
import json
import os
import pathlib
import re
import shutil
import subprocess
from datetime import datetime

REPO = pathlib.Path.home() / "broccoli-core"
BRANCH = "main"
MIN_FREE_MB = 1000
BATCH_FILES = 20
BATCH_MB = 150

IGNORE = [
    r"(^|/)\.git(/|$)",
    r"(^|/)\.ssh(/|$)",
    r"id_ed25519",
    r"id_rsa",
    r"github_pat",
]

def run(cmd, capture=False):
    p = subprocess.run(
        cmd,
        cwd=str(REPO),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=True
    )
    return p.stdout.strip() if capture else None

def free_mb():
    return shutil.disk_usage(REPO).free // (1024 * 1024)

def safe(path):
    return not any(re.search(x, path) for x in IGNORE)

remotes = run(["rclone","listremotes"],True).splitlines()
if not remotes:
    raise SystemExit("No rclone remote configured.")

remote = next((r for r in remotes if "drive" in r.lower() or "google" in r.lower()), remotes[0])
drive_root = remote + "BroccoliWorkspaceBackup"

run(["git","fetch","origin"])

github_files = set(
    run(
        ["git","ls-tree","-r","--name-only","origin/"+BRANCH],
        True
    ).splitlines()
)

entries = json.loads(
    run(
        ["rclone","lsjson","--recursive","--files-only",drive_root],
        True
    )
)

entries.sort(key=lambda e:e["Path"])

count = 0
size = 0

for f in entries:

    rel = f["Path"]

    if rel in github_files:
        continue

    if not safe(rel):
        continue

    if free_mb() < MIN_FREE_MB:
        print("Stopping: storage threshold reached.")
        break

    local = REPO / rel
    local.parent.mkdir(parents=True,exist_ok=True)

    print("COPY",rel)

    run([
        "rclone",
        "copyto",
        drive_root+"/"+rel,
        str(local)
    ])

    count += 1
    size += f.get("Size",0)

    if count>=BATCH_FILES or size>=BATCH_MB*1024*1024:

        subprocess.run(["git","add","-A"],cwd=REPO)

        if subprocess.run(
            ["git","diff","--cached","--quiet"],
            cwd=REPO
        ).returncode:

            subprocess.run(
                [
                    "git","commit",
                    "-m",
                    "Drive sync "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ],
                cwd=REPO
            )

            subprocess.run(
                ["git","push","origin","main"],
                cwd=REPO,
                check=True
            )

        count=0
        size=0

subprocess.run(["git","add","-A"],cwd=REPO)

if subprocess.run(
    ["git","diff","--cached","--quiet"],
    cwd=REPO
).returncode:

    subprocess.run(
        [
            "git","commit",
            "-m",
            "Final Drive sync "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ],
        cwd=REPO
    )

    subprocess.run(
        ["git","push","origin","main"],
        cwd=REPO,
        check=True
    )

print("Finished.")
