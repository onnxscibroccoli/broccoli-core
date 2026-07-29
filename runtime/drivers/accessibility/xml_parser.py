import xml.etree.ElementTree as ET
import hashlib
import logging

logger = logging.getLogger(__name__)

def parse_uiautomator_xml(xml_string):
    """Parses Android uiautomator XML dump into generic semantic node dicts."""
    nodes = []
    if not xml_string or not isinstance(xml_string, str):
        return nodes

    try:
        root = ET.fromstring(xml_string)
        for elem in root.iter('node'):
            a = elem.attrib
            bounds = a.get('bounds', '')
            class_name = a.get('class', '')
            text = a.get('text', '')
            res_id = a.get('resource-id', '')
            
            # Generate stable ID matching Phase 1 cache requirements
            raw_id = f"{res_id}::{class_name}::{bounds}::{text}"
            stable_id = hashlib.md5(raw_id.encode('utf-8')).hexdigest()
            
            nodes.append({
                "stable_id": stable_id,
                "resource_id": res_id,
                "class_name": class_name,
                "package": a.get('package', ''),
                "text": text,
                "content_desc": a.get('content-desc', ''),
                "bounds": bounds,
                "is_focused": a.get('focused') == 'true',
                "is_scrollable": a.get('scrollable') == 'true',
                "is_clickable": a.get('clickable') == 'true',
                "is_enabled": a.get('enabled') == 'true'
            })
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML: {e}")
    return nodes


def is_valid_xml(xml_text):
    if not xml_text:
        return False

    if "<?xml" not in xml_text:
        return False

    if "<hierarchy" not in xml_text:
        return False

    if "</hierarchy>" not in xml_text:
        return False

    return True
