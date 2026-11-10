# Data Model: Web Portal Hardening (Web 1)

No server data is owned by the SPA; shapes come from `src/api/schema.d.ts` (generated).

## Session (browser state)
- `musicstudio.refresh` in `localStorage` — refresh token (rotated after every refresh).
- access token — module memory only.
- user (`Me`) — React state, from `GET /auth/me/` at load and after login.
- Legacy keys `musicstudio-access-token` / `musicstudio-refresh-token` are removed at startup
  (users of the old build are simply asked to log in again).

## Query keys
`["me"]`, `["dashboard"]`, `["students"]`, `["students", id]`, `["students", id, "lessons"]`,
`["payments", studentId|"all"]`. Invalidation: complete lesson → dashboard, students;
register payment → payments, dashboard, students. Logout/login → `clear()`.
