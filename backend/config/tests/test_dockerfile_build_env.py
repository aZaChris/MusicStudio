"""The Docker build imports production settings with throwaway values (`collectstatic`).

When a setting becomes required in `prod.py` and this list is not updated, the image stops
building on the server. This test runs the same import with exactly the Dockerfile's values.
"""

import re
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _build_env() -> dict[str, str]:
    text = (BACKEND_DIR / "Dockerfile").read_text()
    run = re.search(r"RUN env -i(.*?)/opt/venv/bin/python manage\.py collectstatic", text, re.S)
    assert run, "the collectstatic step of the Dockerfile moved: update this test"
    pairs = re.findall(r"\b([A-Z_]+)=(\S+)", run.group(1))
    return {k: v for k, v in pairs if k != "PATH"}


def test_production_settings_load_with_the_dockerfile_build_values():
    env = {"PATH": "/usr/bin:/bin", **_build_env()}

    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr[-600:]
    assert env["DJANGO_SETTINGS_MODULE"] == "config.settings.prod"
