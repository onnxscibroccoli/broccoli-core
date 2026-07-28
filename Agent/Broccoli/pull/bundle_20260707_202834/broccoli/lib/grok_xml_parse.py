import re
COMPOSER_Y = 1850
CHIP = re.compile(r"(?i)^(ask anything|explore |investigate |grok model|xai community|imagine|ask)$|daemon logs|permission model")
def _nodes(xml):
    for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml or ""):
        t, y1 = m.group(1).strip(), int(m.group(3))
        if not t or y1 >= COMPOSER_Y or y1 < 200: continue
        if CHIP.search(t): continue
        yield y1, t
def find_smoke_ok(xml):
    for _, t in sorted(_nodes(xml)):
        if "GROK_SMOKE_OK" in t: return "GROK_SMOKE_OK"
    if 'text="GROK_SMOKE_OK"' in (xml or ""): return "GROK_SMOKE_OK"
    return ""
find_smoke = find_smoke_ok
def extract_hierarchy(blob):
    if not blob: return ""
    if "<?xml" in blob:
        i, j = blob.find("<?xml"), blob.rfind("</hierarchy>")
        if j > i: return blob[i:j+12]
    if "</hierarchy>" in blob:
        j = blob.rfind("</hierarchy>")
        i = blob.rfind("<?xml", 0, j)
        if i >= 0: return blob[i:j+12]
    return blob if "<hierarchy" in blob else ""
