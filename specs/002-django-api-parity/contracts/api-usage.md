# API usage: what the app calls (Django, base `/api/v1`)

| Screen / action | Call | Notes |
| --- | --- | --- |
| Login | `POST /auth/token/` `{email,password}` → `{access,refresh}` | then `GET /auth/me/` |
| Startup | `GET /auth/me/` | 401 → refresh → retry; refresh fails → login |
| Renew | `POST /auth/token/refresh/` `{refresh}` → `{access,refresh}` | single flight; store rotated refresh |
| Logout | `POST /auth/logout/` `{refresh}` → 205 | local clear even on failure |
| Teacher home | `GET /dashboard/` | `week`, `upcoming`, counts, `low_package_students` |
| Complete lesson | `POST /lessons/{id}/complete/` `{note}` | 400/404/409 shown |
| Roster | `GET /students/?is_active=true` (all pages) | follows `next` |
| Student detail | `GET /students/{id}/`, `GET /students/{id}/lessons/` | lessons: plain list |
| Payments list | `GET /payments/` (all pages) | |
| Register payment | `POST /payments/` `{student,amount,date,method,status:"paid"}` | 400 field errors shown |
| Parent portal | `GET /students/` (all pages), `GET /students/{id}/lessons/`, `GET /payments/?student={id}` | read-only |

All shapes: `contract/openapi.yaml` (vendored from `refactor/production-standards`).
