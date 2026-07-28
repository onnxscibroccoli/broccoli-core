#!/usr/bin/env python3
"""Read file, gzip in RAM, upload via rclone rcat or write to DRIVE_COPY_ROOT. Never deletes local."""
import gzip, io, os, subprocess, sys, json, hashlib
from pathlib import Path

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def compress_ram(src: Path) -> bytes:
    data = src.read_bytes()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as gz:
        gz.write(data)
    return buf.getvalue()

def upload_rclone(remote: str, name: str, payload: bytes) -> bool:
    # remote like gdrive:Broccoli/offload/file.tar.gz.gz
    dest = f"{remote.rstrip('/')}/{name}"
    p = subprocess.run(
        ["rclone", "rcat", dest, "--checksum"],
        input=payload,
        capture_output=True,
        timeout=3600,
    )
    return p.returncode == 0

def upload_copy(root: str, name: str, payload: bytes) -> str:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    dest = root / name
    dest.write_bytes(payload)
    return str(dest)

def main():
    if len(sys.argv) < 2:
        print("usage: drive_upload_mem.py <file> [--name remote_name]", file=sys.stderr)
        sys.exit(2)
    src = Path(sys.argv[1]).expanduser()
    if not src.is_file():
        print(json.dumps({"ok": False, "error": "not_a_file", "path": str(src)}))
        sys.exit(1)
    remote = os.environ.get("RCLONE_REMOTE", "").strip()
    copy_root = os.environ.get("DRIVE_COPY_ROOT", "").strip()
    out_name = src.name
    if "--name" in sys.argv:
        i = sys.argv.index("--name")
        if i + 1 < len(sys.argv):
            out_name = sys.argv[i + 1]
    if not out_name.endswith(".gz") and not src.suffix in (".gz", ".tgz"):
        out_name = out_name + ".gz"
    try:
        if src.suffix in (".gz", ".tgz", ".zip"):
            payload = src.read_bytes()
            upload_name = src.name
        else:
            payload = compress_ram(src)
            upload_name = out_name
        method = None
        dest = None
        if remote and subprocess.run(["rclone", "listremotes"], capture_output=True).returncode == 0:
            ok = upload_rclone(remote, upload_name, payload)
            if not ok:
                print(json.dumps({"ok": False, "error": "rclone_rcat_failed", "src": str(src)}))
                sys.exit(1)
            method, dest = "rclone", f"{remote}/{upload_name}"
        elif copy_root:
            dest = upload_copy(copy_root, upload_name, payload)
            method = "copy"
        else:
            print(json.dumps({"ok": False, "error": "no_destination", "hint": "set RCLONE_REMOTE or DRIVE_COPY_ROOT"}))
            sys.exit(1)
        print(json.dumps({
            "ok": True,
            "method": method,
            "src": str(src),
            "dest": dest,
            "upload_name": upload_name,
            "payload_bytes": len(payload),
            "sha256_src": sha256_path(src),
            "local_deleted": False,
        }))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e), "src": str(src)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
