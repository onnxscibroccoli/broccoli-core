#!/usr/bin/env python3
"""Minimum wait: UI dump stable / target node / time cap."""
import hashlib, time
from broccoli_ui_dump import ui_dump, nodes

def dump_fingerprint(xml=None):
    xml = xml if xml is not None else ui_dump()
    h = hashlib.sha256((xml or "").encode("utf-8", errors="replace")).hexdigest()[:16]
    return h, xml

def wait_ui_stable(min_s=0.12, max_s=2.5, poll=0.15, need_stable=2):
    t0 = time.time()
    prev, stable = None, 0
    last_xml = ""
    while time.time() - t0 < max_s:
        h, xml = dump_fingerprint()
        last_xml = xml
        if h == prev:
            stable += 1
            if stable >= need_stable and time.time() - t0 >= min_s:
                return last_xml, time.time() - t0
        else:
            stable = 0
            prev = h
        time.sleep(poll)
    return last_xml, time.time() - t0

def wait_until(predicate, max_s=8.0, poll=0.2, after_tap=False):
    t0 = time.time()
    if after_tap:
        time.sleep(0.08)
    while time.time() - t0 < max_s:
        xml = ui_dump()
        if predicate(xml, nodes(xml)):
            return True, xml, time.time() - t0
        time.sleep(poll)
    return False, ui_dump(), time.time() - t0

def wait_after_tap(max_s=1.8, poll=0.12):
    return wait_ui_stable(min_s=0.1, max_s=max_s, poll=poll, need_stable=1)
