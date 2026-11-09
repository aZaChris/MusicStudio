# Data Model: Mobile App on the Django API (Phase 1)

The app owns no business data. Server shapes come from the generated contract types
(`src/lib/api/schema.d.ts`, `components["schemas"][...]`). This file lists only what the app
keeps itself.

## Session (client state)
- `refresh`: string — persisted in secure storage (key `musicstudio.refresh`).
- `access`: string | null — memory only; replaced on every refresh.
- `user`: `Me` (`id`, `email`, `role`, `preferred_language`, `teacher`, `parent_account`) —
  memory only, fetched from `GET /auth/me/` after login and at startup.
- Transitions: `signed-out` → (login ok) → `signed-in` → (401 + refresh ok) → `signed-in`
  → (refresh fails) → `expired` (login screen with message) → `signed-out`;
  `signed-in` → (logout) → `signed-out` (server logout attempted, storage + cache cleared).

## Query cache keys (TanStack Query)
- `["me"]`, `["dashboard"]`, `["students"]` (all pages), `["students", id]`,
  `["students", id, "lessons"]`, `["payments", {student?}]`.
- Invalidation: complete lesson → dashboard, students; register payment → payments,
  dashboard, students. Logout → `clear()` everything.

## ApiError (client)
- `status` (0 = network), `code` (server `code` if any), `detail` (server text if any),
  `fieldErrors` (DRF field → messages). Mapped to translated UI messages.
