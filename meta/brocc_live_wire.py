
#!/usr/bin/env python3
import subprocess, sys, hashlib
from pathlib import Path
META = Path.home() / "broccoli/meta"
IN, LOG = META / "inbox/from_mac", META / "live_wire.log"
CLIP_H = META / ".clip_hash"

def log(msg):
    line = "%s %s\n" % (__import__("time").strftime("%F %T"), msg)
    LOG.open("a").write(line)
    print(msg.strip())

def run_file(f):
    import importlib.util
    spec = importlib.util.spec_from_file_location("st", META / "brocc_state.py")
    st = importlib.util.module_from_spec(spec); sys.modules["st"] = spec; spec.loader.exec_module(st)
    st.set_phase("running")
    lines = []
    for ln in f.read_text(errors="replace").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"): continue
        if s.startswith(("python3 ", "brocc ", "pkg ", "termux-", "bash ", "rish ")):
            lines.append(s)
    if lines:
        script = META / ".grok_exec.sh"
        script.write_text("\n".join(lines) + "\n")
        subprocess.run(["bash", str(script)], stdout=LOG.open("a"), stderr=subprocess.STDOUT, timeout=600)
    done = Path(str(f) + ".done")
    f.rename(done)
    st.set_phase("await_grok")
    subprocess.run([sys.executable, str(META / "brocc_loop_emit.py"), "--force"], timeout=120)
    log("live_wire OK %s" % done.name)

def main():
    for name in ("grok_commands.sh", "grok_reply.txt"):
        f = IN / name
        if f.is_file() and not Path(str(f) + ".done").is_file():
            run_file(f); return
    if __import__("os").environ.get("LIVE_WIRE_CLIP") == "1":
        try:
            clip = subprocess.check_output(["termux-clipboard-get"], text=True, timeout=5)
        except Exception:
            return
        if clip.strip().startswith("BROCC_GROK:"):
            h = hashlib.sha256(clip.encode()).hexdigest()
            if CLIP_H.is_file() and CLIP_H.read_text().strip() == h: return
            CLIP_H.write_text(h)
            tmp = IN / "grok_commands.from_clip.sh"
            tmp.write_text(clip.split(":", 1)[-1].strip())
            run_file(tmp)

if __name__ == "__main__":
    main()
