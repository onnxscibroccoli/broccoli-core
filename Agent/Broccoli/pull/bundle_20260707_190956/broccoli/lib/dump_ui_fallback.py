from pathlib import Path
HOME = Path.home()
CANDIDATES = [
    HOME / "broccoli/ui/last_ui.xml",
    HOME / "broccoli/ui/last.xml",
    Path("/sdcard/broccoli_ui.xml"),
    Path("/data/local/tmp/broccoli_ui.xml"),
]
MIN_OK = 8000
def read_best_xml():
    best_path, best_n, best_text = "", 0, ""
    for p in CANDIDATES:
        if p.is_file():
            data = p.read_bytes()
            n = len(data)
            if n > best_n:
                best_n, best_path = n, str(p)
                best_text = data.decode("utf-8", errors="replace")
    return best_text, best_n, best_path
def fallback_if_empty(live, live_bytes):
    if live_bytes >= MIN_OK and live and "<hierarchy" in live:
        return live, live_bytes, "live"
    text, n, path = read_best_xml()
    if n >= MIN_OK and "<hierarchy" in text:
        return text, n, "fallback:" + path
    return live or "", live_bytes, "empty"
