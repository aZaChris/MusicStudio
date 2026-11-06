"""Container health probes. Standard library only (the slim image has no curl).

Usage:
    python docker/healthcheck.py http /health/live/
    python docker/healthcheck.py beat /tmp/celerybeat-schedule 1200
"""

import glob
import os
import sys
import time
import urllib.request


def check_http(path: str) -> bool:
    url = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}{path}"
    request = urllib.request.Request(url, headers={"Host": "localhost"})
    with urllib.request.urlopen(request, timeout=4) as response:  # noqa: S310 - fixed local URL
        return bool(response.status == 200)


def check_beat(schedule_prefix: str, max_age_seconds: int) -> bool:
    """Beat persists its schedule after sending tasks; a stale file means a stuck beat.

    The dbm backend may add suffixes (.db, .dat, .dir), hence the glob.
    """
    files = glob.glob(f"{schedule_prefix}*")
    if not files:
        return False
    newest = max(os.path.getmtime(path) for path in files)
    return time.time() - newest < max_age_seconds


def main(argv: list[str]) -> int:
    try:
        if argv[1] == "http":
            healthy = check_http(argv[2])
        elif argv[1] == "beat":
            healthy = check_beat(argv[2], int(argv[3]))
        else:
            return 2
    except Exception as exc:
        print(f"unhealthy: {exc}", file=sys.stderr)
        return 1
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
