# API Contract Changes: Production Foundations (Phase 1)

Base contract: `specs/001-musicstudio-mvp/contracts/api.md`. Only differences are listed.
The live contract is the OpenAPI schema at `/api/schema/` (Swagger UI at `/api/docs/`).

## New infrastructure endpoints (outside `/api/v1/`, unauthenticated, not throttled)

| Method | Path | 200 | Failure |
|---|---|---|---|
| GET | `/health/live/` | `{"status": "ok"}` | — (process down = no answer) |
| GET | `/health/ready/` | `{"status": "ok", "checks": {"database": "ok", "redis": "ok"}}` | 503, failing check reported as `"error"` |

## Behaviour changes on existing endpoints

| Endpoint | Before | After |
|---|---|---|
| `POST/PATCH /api/v1/lessons/`, `/payments/`, `/packages/` with an out-of-scope `student` or `package` | 201/200, data written in another tenant | 400 `{"student": ["Invalid pk …"]}`, nothing written |
| `POST /api/v1/lessons/` with a `package` of another student | accepted | 400 `{"package": [...]}` |
| `POST /api/v1/packages/` without `lessons_remaining` | 400 (field required) | 201, `lessons_remaining = total_lessons` |
| `PATCH /api/v1/packages/{id}/` with `lessons_remaining` | value written | field ignored (read-only) |
| `GET /api/v1/lessons/?week=<invalid>` | 500 | 400 `{"week": [...]}` |
| `GET /api/v1/studio/`, `/studio/teachers/` as owner without teacher profile/studio | 500 | 404 |
| `POST /api/v1/auth/token/` beyond the login rate | unlimited | 429 with `Retry-After` |
| Any endpoint beyond anon/user rates | unlimited | 429 |
| `/admin/` | fixed path | path from `DJANGO_ADMIN_URL` (default `admin/`) |

Response shapes of successful requests are unchanged.
