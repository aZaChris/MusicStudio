# Quickstart / Validation: Production Foundations (Phase 1)

## Prerequisites
- Python 3.12 and `uv`; PostgreSQL 16 reachable (local or `docker compose up db redis`).
- For the stack checks: Docker with Compose v2.

## 1. Quality gate locally (same as CI)

```bash
cd backend
uv sync --frozen
export DATABASE_URL=postgres://musicstudio:musicstudio@localhost:5432/musicstudio
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run
uv run pytest            # coverage gate: 90%
```
Expected: all green. `pre-commit run --all-files` from the repo root runs the fast subset.

## 2. Security regressions (US1, US5)
`uv run pytest -k "cross_tenant or throttle"` — every cross-tenant write is 400 and the
login throttle returns 429.

## 3. Query budgets (US2)
`uv run pytest -k num_queries` — roster/lessons/packages/payments/dashboard have fixed
query counts for 1 and 25 rows.

## 4. Dev stack
```bash
cp .env.example .env          # fill DJANGO_SECRET_KEY etc.
docker compose up --build     # db, redis, backend, worker, beat
curl localhost:8000/health/live/ ; curl localhost:8000/health/ready/
docker compose --profile frontend up   # optional: the isolated React SPA
```
Expected: `docker compose ps` shows every service `healthy`.

## 5. Production stack (Coolify definition) locally
```bash
docker compose -f docker-compose.coolify.yml config   # fails, naming missing required vars
# set the required vars (see .env.example "production"), then:
docker compose -f docker-compose.coolify.yml up -d --build
docker compose -f docker-compose.coolify.yml ps       # all healthy, no published ports
docker compose -f docker-compose.coolify.yml exec backup ls /backups/daily
```

## 6. Coolify
New resource → Docker Compose → this repo, branch, compose file `docker-compose.coolify.yml`.
Set the domain on the `backend` service (e.g. `https://api.example.com:8000`), fill the
required variables, deploy. Checks: `https://<domain>/health/ready/` returns 200.

## Not verifiable in the authoring environment
Docker is not available in the WSL environment where phase 1 was written; steps 4–6 must
be run on a machine with Docker. Steps 1–3 were run and are green.
