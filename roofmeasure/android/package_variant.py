#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate a build-time manifest for either stable or isolated alpha package."""
import sys
import xml.etree.ElementTree as ET

BASE = "com.ian.roofmeasure"
ALPHA = BASE + ".alpha"
ANDROID = "http://schemas.android.com/apk/res/android"
NAME = "{" + ANDROID + "}name"
ET.register_namespace("android", ANDROID)


def write_variant(input_path, output_path, package):
    if package not in (BASE, ALPHA):
        raise ValueError("unsupported Android package: " + package)
    tree = ET.parse(input_path)
    root = tree.getroot()
    if root.attrib.get("package") != BASE:
        raise ValueError("unexpected base package in source manifest")
    root.attrib["package"] = package
    app = root.find("application")
    if app is None:
        raise ValueError("no application in manifest")
    if package == ALPHA:
        app.set("{" + ANDROID + "}label", "RoofMeasure Alpha")
    for kind in ("activity", "provider"):
        for component in app.iter(kind):
            name = component.attrib.get(NAME, "")
            if name.startswith("."):
                component.set(NAME, BASE + name)
            if kind == "provider":
                authority_key = "{" + ANDROID + "}authorities"
                if component.attrib.get(authority_key) != BASE + ".reports":
                    raise ValueError("unexpected source provider authority")
                component.set(authority_key, package + ".reports")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: package_variant.py INPUT.xml OUTPUT.xml PACKAGE")
    write_variant(sys.argv[1], sys.argv[2], sys.argv[3])
