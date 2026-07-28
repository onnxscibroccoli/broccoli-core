import subprocess
def toast(msg):
    try: subprocess.run(["termux-toast", "-g", "north", msg], timeout=8, capture_output=True)
    except: pass
