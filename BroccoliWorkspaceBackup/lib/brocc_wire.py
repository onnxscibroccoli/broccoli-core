from pathlib import Path
import re
LIB = Path.home() / "broccoli" / "lib"
CL = LIB / "closed_loop.py"
if not CL.is_file():
    print("no closed_loop")
    raise SystemExit(0)
s = CL.read_text(encoding="utf-8", errors="replace")
if "catalog_loop_hook" in s:
    print("already wired")
    raise SystemExit(0)
inj = "\nimport sys\nfrom pathlib import Path as _P\nsys.path.insert(0, str(_P.home() / \"broccoli\" / \"lib\"))\nfrom catalog_loop_hook import enrich_outgoing, maybe_catalog, is_catalog_ok\n"
if "def send_text" in s:
    s = re.sub(r"(def send_text\(text:\s*str\)[^:]*:\n)", r"\1    text = enrich_outgoing(text)\n", s, 1)
if "def one_round" in s:
    s = re.sub(r"(def one_round\([^)]*\)[^:]*:\n)", r"\1    maybe_catalog(n)\n", s, 1)
for old in ('re.search(r"(?i)LOOP_OK", msg)', "re.search(r'(?i)LOOP_OK', msg)"):
    if old in s:
        s = s.replace(old, '(re.search(r"(?i)LOOP_OK", msg) or is_catalog_ok(msg))', 1)
m = re.search(r"^(from __future__.*\n)+", s) or re.search(r"^#!/.*\n", s)
pos = m.end() if m else 0
CL.write_text(s[:pos] + inj + s[pos:], encoding="utf-8")
print("PATCH closed_loop ok")
