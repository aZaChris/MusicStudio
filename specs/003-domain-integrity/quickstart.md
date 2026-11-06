# Quickstart / Validation: Domain Integrity (Phase 2)

Prerequisites and the full gate are as in `specs/002-production-foundations/quickstart.md` §1.
The database user must be allowed to `CREATE EXTENSION btree_gist` (true for the Compose and
CI Postgres superuser).

## 1. Overlap guarantee (US1)
`uv run pytest -k overlap` — teacher/student overlaps → 409, back-to-back and cancelled slots
accepted; the concurrency test fires two simultaneous bookings: exactly one 201.

Manual: `uv run python manage.py dbshell` → `\d lessons_lesson` shows both `EXCLUDE USING
gist` constraints.

## 2. Tenancy (US2)
`uv run pytest -k "tenant or cross_tenant or num_queries"` — every teacher/student has a
studio; phase 1 isolation tests pass; query budgets unchanged.

## 3. Permissions (US3) and payments (US4)
`uv run pytest -k "reassign or teacher_cap or transition"`.

## 4. Contract (US5)
```bash
uv run python manage.py spectacular --settings=config.settings.test --file openapi.yaml
git diff --exit-code openapi.yaml    # what CI does
```
Open `/api/docs/`: endpoints grouped by domain, error responses listed.
