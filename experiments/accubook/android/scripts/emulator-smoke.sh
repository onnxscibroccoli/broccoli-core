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
    # Hosted emulator sometimes shows an ANR for its *launcher* Quickstep
    # during first boot. Do not hide an ANR from Accubook itself.
    if any("Quickstep isn't responding" in node.attrib.get('text','')
           for node in root.iter('node')):
        waits=[node for node in root.iter('node')
               if node.attrib.get('text','')=='Wait']
        if waits:
            box=re.findall(r'\\[(\\d+),(\\d+)\\]',waits[0].attrib.get('bounds',''))
            if len(box)==2:
                x=(int(box[0][0])+int(box[1][0]))//2
                y=(int(box[0][1])+int(box[1][1]))//2
                print('ANDROID_EMULATOR_LAUNCHER_RECOVERY: Wait Quickstep',x,y)
                subprocess.run(['adb','shell','input','tap',str(x),str(y)],check=True)
                time.sleep(3)
                continue
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


# Focused job rail is horizontally scrollable; choose a tab by visible label.
tap_job_tab() {
  local label="$1"
  LABEL="$label" python3 - <<'PY'
import os,re,subprocess,time,xml.etree.ElementTree as ET
label=os.environ['LABEL']
for attempt in range(11):
    subprocess.run(['adb','shell','uiautomator','dump','/sdcard/accubook-window.xml'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    root=ET.fromstring(subprocess.check_output(['adb','exec-out','cat','/sdcard/accubook-window.xml']))
    rows=[x for x in root.iter('node') if 'HorizontalScrollView' in x.attrib.get('class','')]
    if not rows:
        # Long content sections can scroll the fixed top rail out of the
        # accessibility tree. Return toward the top before deciding it is missing.
        subprocess.run(['adb','shell','input','swipe','500','540','500','1510','350'],
            check=True)
        time.sleep(.7)
        continue
    rail=rows[0]
    points=re.findall(r'\[(-?\d+),(-?\d+)\]',rail.attrib.get('bounds',''))
    if len(points)!=2: raise SystemExit('No rail bounds')
    left,top=map(int,points[0]);right,bottom=map(int,points[1])
    center=(top+bottom)//2
    for node in root.iter('node'):
        if label.lower() not in (node.attrib.get('text','')+' '+node.attrib.get('content-desc','')).lower(): continue
        bounds=re.findall(r'\[(-?\d+),(-?\d+)\]',node.attrib.get('bounds',''))
        if len(bounds)!=2: continue
        x1,y1=map(int,bounds[0]);x2,y2=map(int,bounds[1])
        x=(x1+x2)//2;y=(y1+y2)//2
        if left+20<x<right-20 and top<y<bottom:
            print('TAB',label,x,y)
            subprocess.run(['adb','shell','input','tap',str(x),str(y)],check=True)
            exit(0)
    # Attempt both directions so the test is deterministic even after a prior tab switch.
    forward=attempt<6
    xfrom=right-35 if forward else left+35
    xto=left+35 if forward else right-35
    subprocess.run(['adb','shell','input','swipe',str(xfrom),str(center),
       str(xto),str(center),'330'],check=True)
    time.sleep(.7)
raise SystemExit('Missing job tab: '+label)
PY
}
# Fresh empty workspaces now display the offline setup before the home screen.
# Exercise Save, then continue the existing end-to-end job workflow.
tap_node 'Save setup'
assert_visible 'Accubook'
tap_node 'Try fictional sample job'
tap_node 'Create sample'
assert_visible 'Sample Customer'
assert_visible 'Job history'
tap_node 'DEMO - Gutter'
assert_visible 'Reschedule / change time'
assert_visible 'Change job status'
tap_node 'Change job status'
tap_node 'In Progress'
assert_visible 'In Progress'
tap_job_tab 'Photos'
assert_visible 'Add photo from device'
tap_job_tab 'Money'
assert_visible 'Estimate and invoice'
assert_visible 'New change order'
tap_job_tab 'Notes'
assert_visible 'Edit field notes'
tap_job_tab 'Checklist'
assert_visible 'Custom checklist and fields'
adb shell am force-stop com.accubook.crm
adb shell am start -n com.accubook.crm/.MainActivity
sleep 2
assert_visible 'In Progress'
# Restart lands on Home; the previous long job UI may have kept its scroll
# position. Seek top before looking for the global search button.
for n in 1 2 3 4 5 6 7 8; do
  adb shell input swipe 500 440 500 1520 160
done
tap_node 'Find anything'
assert_visible 'Search this device'
echo "ACCUBOOK_EMULATOR_SMOKE_PASS: launch/demo/job/changes/notes/restart/local-lookup"
