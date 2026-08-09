class HealthMonitor:
    def check(self):
        return {
            "status": "healthy",
            "uptime": 0,
            "components": 12,
            "accessibility": True,
            "governor": True
        }
