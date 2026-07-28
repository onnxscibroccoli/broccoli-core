import subprocess

from problem_solver import Evidence


def android_state_collector(issue):

    evidence = []

    try:
        pkg = subprocess.run(
            ["rish", "-c", "dumpsys window | grep mCurrentFocus"],
            capture_output=True,
            text=True,
            timeout=5
        )

        evidence.append(
            Evidence(
                source="android",
                key="foreground_window",
                value=pkg.stdout.strip(),
                confidence=0.95
            )
        )

    except Exception:

        evidence.append(
            Evidence(
                source="android",
                key="foreground_window",
                value="unknown",
                confidence=0.20
            )
        )

    return evidence
