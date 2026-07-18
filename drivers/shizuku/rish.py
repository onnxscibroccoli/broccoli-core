import subprocess
import os

class RishDriver:
    def __init__(self):
        self.rish_path = "/data/data/com.termux/files/usr/bin/rish"
        self.available = self._check_rish()

    def _check_rish(self):
        if os.path.exists(self.rish_path) and os.access(self.rish_path, os.X_OK):
            print("✅ rish (Shizuku) detected and executable")
            return True
        print("⚠️  rish not found. Run Shizuku export in Termux first.")
        return False

    def run(self, command: str, as_root=False):
        """Run command via rish with Shizuku privileges"""
        if not self.available:
            return {"success": False, "error": "rish not available"}

        try:
            full_cmd = [self.rish_path, "-c", command]
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "code": result.returncode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def system_info(self):
        """Quick system diagnostics via Shizuku"""
        return self.run("getprop ro.build.version.release && whoami")
