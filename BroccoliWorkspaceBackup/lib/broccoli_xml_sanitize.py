import re
_INVALID_XML_RE = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x84\x86-\x9F\uD800-\uDFFF\uFDD0-\uFDEF\uFFFE\uFFFF]"
)

def extract_hierarchy(raw):
    if not raw:
        return ""
    i = raw.find("<?xml")
    if i < 0:
        i = raw.find("<hierarchy")
    if i < 0:
        return ""
    raw = raw[i:]
    j = raw.rfind("</hierarchy>")
    if j >= 0:
        raw = raw[: j + len("</hierarchy>")]
    return raw

def sanitize_xml(xml):
    xml = extract_hierarchy(xml)
    if not xml:
        return ""
    xml = _INVALID_XML_RE.sub("", xml)
    # fix lone & not part of entity
    xml = re.sub(r"&(?!amp;|lt;|gt;|apos;|quot;|#)", "&amp;", xml)
    return xml

def parse_nodes_regex(xml, pkg_filter=None):
    """Fallback when ElementTree fails."""
    xml = sanitize_xml(xml)
    if not xml:
        return []
    nodes = []
    for m in re.finditer(r'<node\b([^>]*)/?>', xml, re.I):
        attrs = m.group(1)
        def attr(name):
            q = re.search(rf'{name}="([^"]*)"', attrs) or re.search(rf"{name}='([^']*)'", attrs)
            return (q.group(1) if q else "").strip()
        b = attr("bounds")
        bm = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if not bm:
            continue
        x1,y1,x2,y2 = map(int, bm.groups())
        pkg = attr("package")
        if pkg_filter and pkg_filter not in pkg:
            continue
        nodes.append({
            "text": attr("text"),
            "desc": attr("content-desc"),
            "rid": attr("resource-id"),
            "cls": attr("class"),
            "pkg": pkg,
            "clickable": attr("clickable") == "true",
            "enabled": attr("enabled") != "false",
            "focusable": attr("focusable") == "true",
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "cx": (x1+x2)//2, "cy": (y1+y2)//2,
            "el": None,
        })
    return nodes
