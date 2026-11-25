# Case study: three bugs that tests alone did not see coming

MusicStudio is a Django REST API for music teachers and small studios: lessons, prepaid
packages, payments and a read-only parent portal. It runs on PostgreSQL, Redis and Celery,
deployed with Docker Compose on a self-hosted Coolify server. This page tells three real
problems found while building it, what caused them, how the cause was confirmed and what
changed. Each one is written up in full, in Italian, in [`docs/knowledge-base/`](knowledge-base/README.md).
No number below is estimated: each comes from a test or a log quoted in those entries.

## 1. A 60-minute lesson that lasted two hours

**Symptom.** A test booked a lesson at 00:30 UTC on 25 October 2026, the night clocks go back in
Italy, for 60 minutes. It was stored with an end time of 02:30 UTC. The next booking, at 01:30
UTC, got a `409 Conflict` although that slot was free.

**Root cause.** DRF converts incoming datetimes to the current time zone, `Europe/Rome`. In
Python, adding a `timedelta` to an aware datetime with `zoneinfo` is *wall-clock* arithmetic:
02:30 CEST plus 60 minutes is 03:30 local time. But that night at 03:00 CEST the clock goes back
to 02:00 CET, so 03:30 CET is two real hours later.

**How it was confirmed.** A temporary test printed the database row and the API response:
`start_time` 00:30 UTC, `end_time` 02:30 UTC.

**Fix.** `end_of(start, minutes)` in `backend/apps/lessons/services.py` converts to UTC before
adding. The lesson's duration subtracts in UTC too, since subtracting two datetimes with the same
`tzinfo` is also wall-clock arithmetic.

**Lesson.** Durations are computed in UTC; local time is only for calendar ideas such as "Monday
at midnight". A test on the night of the clock change is cheap and finds this class of bug.

## 2. Two simultaneous bookings deadlocked instead of returning 409

**Symptom.** The database refuses overlapping lessons with a PostgreSQL *exclusion constraint*.
A test with two threads booking the same slot expected one `201` and one `409`. It got
`OperationalError: deadlock detected ... while checking exclusion constraint`.

**Root cause.** With an exclusion constraint PostgreSQL inserts the row first and checks the
constraint afterwards. Each transaction finds the other's uncommitted row and waits for it to
finish, so they wait for each other. PostgreSQL detects the cycle and aborts one with SQLSTATE
`40P01`. With a `UNIQUE` constraint the second writer usually just waits and fails cleanly; with
exclusion constraints a deadlock is a documented possible outcome.

**How it was confirmed.** The traceback showed "Process A waits for ShareLock on transaction X;
blocked by process B" and the reverse, while checking `lesson_no_teacher_overlap`.

**Fix.** `_guarded_write` runs the write inside a savepoint and retries up to twice on a deadlock.
On the retry the winner's row is visible, the constraint raises a normal violation, and that
becomes a `409`. The concurrent test now passes 5 times out of 5, and three unit tests cover the
retry, running out of retries, and other integrity errors.

**Lesson.** A constraint that protects against concurrent writes must be tested with real
concurrent writes, on separate connections. Code that translates database errors must expect a
deadlock, not only a violation.

## 3. A rate limit that did not exist, and said nothing

**Symptom.** While writing tests for the cash-register export (phase 8), every request returned
`200`, even after dozens of calls by the same user. The export has its own rate-limit scope,
`register_export`. There was no error and no warning: the limit simply was not there.

**Root cause.** The API's throttles *fail open*: if the cache (Redis) is down, the request passes
and the error is logged, so a Redis outage cannot take the whole API down. DRF reads a scope's
rate inside `allow_request`, not at start-up. A scope missing from the settings raises
`ImproperlyConfigured` there, and the fail-open wrapper caught it like any other error. A scope
written on a view but forgotten in the settings was therefore a limit that silently did not
exist.

**How it was confirmed.** The first rate-limit test never saw a `429` until the rate was added to
the test settings; then the sixth request returned `429`. The cause was read in DRF's code and in
the fail-open wrapper. The silence itself was not reproduced with a dedicated test, and the
write-up says so.

**Fix.** The rate is configured in base and test settings and documented in `.env.example`. One
test checks that the scope exists in the production settings; another proves the sixth request
gets `429` and that another user has a separate counter.

**Lesson.** A mechanism that fails open also hides its own configuration errors. Every new
throttle scope ships with a test that proves its `429`. Deciding what to let through when
infrastructure is down is a choice; it must not extend to a typo in the configuration.

## What these have in common

None of the three showed up in a happy-path test. Each needed a test built around the edge where
the system meets the outside world: the calendar, concurrency, and configuration. That is now how
features are tested here, and it is why the knowledge base exists: the cause and the proof are
written down, so the same bug is recognised the second time.
