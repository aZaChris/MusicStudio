# API Contract Changes: Domain Integrity (Phase 2)

The full contract is now committed at `backend/openapi.yaml` (generated, CI-checked).

## Error shapes (documented for every operation where they apply)

| Status | When | Body |
|---|---|---|
| 400 | invalid input, invalid transition | `{"<field>": ["message"]}` or `["message"]` |
| 401 | missing/invalid token | `{"detail": "..."}` |
| 403 | role/object not allowed | `{"detail": "..."}` |
| 404 | object outside the tenant or missing | `{"detail": "..."}` |
| 409 | lesson overlaps an active lesson | `{"detail": "...", "code": "lesson_overlap"}` |
| 429 | rate limit | `{"detail": "..."}` + `Retry-After` |

## Lessons
- Request/response keep `duration_minutes`; response adds read-only `end_time`.
- `POST/PUT/PATCH /api/v1/lessons/` and `POST /lessons/{id}/complete/`: **409** when the
  interval overlaps an active lesson of the same teacher or student.

## Students
- Response adds read-only `studio`.
- New `POST /api/v1/students/{id}/reassign/` body `{"teacher": <id>}` — studio owner only;
  200 with the student; 400 if the teacher is not in the owner's studio; 403 for other roles;
  404 outside the studio.

## Payments
- `PATCH/PUT /api/v1/payments/{id}/` with a disallowed status change → 400
  `{"status": ["Cannot change status from paid to pending."]}`.

## Tags
`accounts`, `studios`, `students`, `packages`, `lessons`, `payments` (one per domain app).
