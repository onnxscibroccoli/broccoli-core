import subprocess
import logging

logger = logging.getLogger("shizuku.actions")


def run(command, timeout=5):
    """
    Execute a documented Android shell action through rish/Shizuku.
    """

    try:
        result = subprocess.run(
            [
                "rish",
                "-c",
                command
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode
        }

    except Exception as e:
        logger.warning(
            "Shizuku action failed: %s",
            e
        )

        return {
            "success": False,
            "error": str(e)
        }


def tap(x, y):
    return run(
        f"input tap {x} {y}"
    )


def text(value):
    escaped = value.replace(
        " ",
        "%s"
    )

    return run(
        f"input text {escaped}"
    )
