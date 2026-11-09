"""Load test of the main read paths (ADR-022).

Data: `manage.py seed_loadtest` (users lt-*, password `loadtest-password`), run with the
SAME settings as the server under test: password hashes depend on PASSWORD_HASHERS, and
the test settings' MD5 hashes are rejected by production settings (every login -> 401).
Run headless, e.g.:

    uv run --group load locust -f loadtest/locustfile.py --headless \
        -u 50 -r 5 -t 5m --host http://localhost:8000 --csv ../docs/loadtest/<date>/run

Rate limits must be raised for the run (THROTTLE_*): all simulated users share one IP, and
the goal is to measure capacity, not the throttles. Never point this at production.
"""

import random

from locust import HttpUser, between, task

PASSWORD = "loadtest-password"  # noqa: S105 - seed data, never production
STUDIOS, TEACHERS = 10, 5  # must match the seed


def _random_staff_email() -> str:
    studio, teacher = random.randrange(STUDIOS), random.randrange(TEACHERS)  # noqa: S311
    return (
        f"lt-owner-{studio}@example.com"
        if teacher == 0
        else (f"lt-teacher-{studio}-{teacher}@example.com")
    )


class StaffUser(HttpUser):
    """A teacher or studio owner using the app during the day: ~1 action every 1-3 s."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        res = self.client.post(
            "/api/v1/auth/token/",
            json={"email": _random_staff_email(), "password": PASSWORD},
            name="POST /auth/token/",
        )
        res.raise_for_status()
        self.refresh = res.json()["refresh"]
        self.client.headers["Authorization"] = f"Bearer {res.json()['access']}"

    @task(4)
    def week_calendar(self) -> None:
        self.client.get("/api/v1/lessons/", name="GET /lessons/ (this week)")

    @task(2)
    def other_week(self) -> None:
        week = random.choice(["2026-09-07", "2026-10-12", "2026-11-23"])  # noqa: S311
        self.client.get(f"/api/v1/lessons/?week={week}", name="GET /lessons/?week=")

    @task(2)
    def upcoming(self) -> None:
        self.client.get("/api/v1/lessons/upcoming/", name="GET /lessons/upcoming/")

    @task(3)
    def dashboard(self) -> None:
        self.client.get("/api/v1/dashboard/", name="GET /dashboard/")

    @task(2)
    def packages(self) -> None:
        self.client.get("/api/v1/packages/", name="GET /packages/")

    @task(2)
    def students(self) -> None:
        self.client.get("/api/v1/students/", name="GET /students/")

    @task(1)
    def renew_session(self) -> None:
        res = self.client.post(
            "/api/v1/auth/token/refresh/",
            json={"refresh": self.refresh},
            name="POST /auth/token/refresh/",
        )
        if res.ok:  # rotation: keep the new pair, the old refresh is now blacklisted
            self.refresh = res.json()["refresh"]
            self.client.headers["Authorization"] = f"Bearer {res.json()['access']}"
