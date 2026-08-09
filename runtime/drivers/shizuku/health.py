import subprocess


def check():
    try:
        result = subprocess.run(
            [
                "rish",
                "-c",
                "echo shizuku_ok"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        return {
            "available": result.stdout.strip() == "shizuku_ok",
            "mode": "rish"
        }

    except Exception as e:
        return {
            "available": False,
            "mode": "unavailable",
            "error": str(e)
        }
