#!/usr/bin/env bash
# Non-destructive CI UI smoke against a NEW, empty Android emulator instance.
set -euo pipefail

export APK_PATH="${APK_PATH:-app/build/outputs/apk/debug/app-debug.apk}"
test -f "$APK_PATH"
adb wait-for-device
adb shell settings put system font_scale 1.2 || true
adb install -r "$APK_PATH"
adb shell am force-stop com.accubook.crm || true
adb shell input keyevent KEYCODE_WAKEUP || true
adb shell wm dismiss-keyguard || true
adb shell input keyevent 82 || true
adb shell am start -W -n com.accubook.crm/.MainActivity
sleep 5

# Look up a semantic accessibility node rather than hard-coding display pixels.
tap_node() {
  local label="$1"
  LABEL="$label" python3 - <<'PY'
import os, re, subprocess, time, xml.etree.ElementTree as ET
label = os.environ['LABEL']
for attempt in range(28):
    subprocess.run(['adb','shell','uiautomator','dump','/sdcard/accubook-window.xml'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    xml = subprocess.check_output(['adb','exec-out','cat','/sdcard/accubook-window.xml'])
    root = ET.fromstring(xml)
    target = None
    for element in root.iter('node'):
        if label.lower() in (element.attrib.get('text','') + ' ' + element.attrib.get('content-desc','')).lower():
            target = element
            break
    if target is not None:
        bounds = re.findall(r'\[(\d+),(\d+)\]', target.attrib.get('bounds',''))
        if len(bounds) == 2:
            x = (int(bounds[0][0]) + int(bounds[1][0])) // 2
            y = (int(bounds[0][1]) + int(bounds[1][1])) // 2
            height=int(re.search(r'(?:Physical|Override) size: \d+x(\d+)',
                subprocess.check_output(['adb','shell','wm','size']).decode()).group(1))
            if 95 < y < height-170:
                print('TAP',label,x,y)
                subprocess.run(['adb','shell','input','tap',str(x),str(y)],check=True)
                exit(0)
            print('OFFSCREEN_NODE',label,x,y,'screen_height',height)
    # Scroll to the target; accessibility XML can contain off-screen bounds.
    if attempt < 24:
        subprocess.run(['adb','shell','input','swipe','500','1550','500','560','350'],check=True)
    else:
        subprocess.run(['adb','shell','input','swipe','500','560','500','1500','350'],check=True)
    time.sleep(1)
print('VISIBLE_NODES:', [(el.attrib.get('text'), el.attrib.get('content-desc'), el.attrib.get('bounds')) for el in root.iter('node') if el.attrib.get('text') or el.attrib.get('content-desc')][:100])
subprocess.run(['adb','shell','dumpsys','activity','activities'])
log = subprocess.run(['adb','logcat','-d','-t','200','-s','AndroidRuntime:E','ActivityTaskManager:I'],
                     capture_output=True,text=True)
print('ANDROID_LOGS:', log.stdout[-6000:])
raise SystemExit('UI element not found: '+label)
PY
}
assert_visible() {
  local label="$1"
  LABEL="$label" python3 - <<'PY'
import os, subprocess, time
label=os.environ['LABEL']
for attempt in range(8):
    subprocess.run(['adb','shell','uiautomator','dump','/sdcard/accubook-window.xml'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    raw = subprocess.check_output(['adb','exec-out','cat','/sdcard/accubook-window.xml']).decode()
    if label.lower() in raw.lower():
        print('VISIBLE',label)
        exit(0)
    if attempt<24:
        subprocess.run(['adb','shell','input','swipe','500','1550','500','570','350'],check=True)
    else:
        subprocess.run(['adb','shell','input','swipe','500','570','500','1500','350'],check=True)
    time.sleep(1)
print('VISIBLE_NODES:', [(el.attrib.get('text'),el.attrib.get('content-desc')) for el in __import__('xml.etree.ElementTree',fromlist=['ElementTree']).fromstring(raw).iter('node') if el.attrib.get('text') or el.attrib.get('content-desc')][:100])
logs=subprocess.run(['adb','logcat','-d','-t','150','-s','AndroidRuntime:E','ActivityTaskManager:I'], capture_output=True,text=True)
print('ANDROID_LOGS:',logs.stdout[-6000:])
raise SystemExit('Expected UI text missing: '+label)
PY
}

assert_visible 'Accubook'
tap_node 'Try fictional sample job'
tap_node 'Create sample'
assert_visible 'Sample Customer'
assert_visible 'Job history'
tap_node 'DEMO - Gutter'
assert_visible 'Reschedule / change time'
assert_visible 'Your customizable job checklist'
assert_visible 'Change job status'
tap_node 'Change job status'
tap_node 'In Progress'
assert_visible 'In Progress'
assert_visible 'Estimate and invoice'
assert_visible 'Add photo from device'
adb shell am force-stop com.accubook.crm
adb shell am start -n com.accubook.crm/.MainActivity
sleep 2
assert_visible 'In Progress'
echo "ACCUBOOK_EMULATOR_SMOKE_PASS: launch/demo/customer/job/status/restart"
