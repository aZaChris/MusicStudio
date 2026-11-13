# MusicStudio — web portal

The React single-page app for MusicStudio: teachers and studio owners manage lessons, students
and payments; parents see their children's lessons and payments (read-only). It is a client of
the Django REST API in `../backend` and holds no business rules of its own: the API decides who
can see and change what.

## Stack

React 19 · TypeScript (strict) · Vite 8 · TanStack Query · react-router 7 · i18next (EN/IT) ·
Vitest + Testing Library · oxlint · Prettier. Production: static files served by a pinned,
non-root `nginx-unprivileged` image.

## Layout

```text
src/api/          client.ts   fetch wrapper, ApiError, session (refresh rotation, single flight)
                  schema.d.ts GENERATED from ../backend/openapi.yaml — do not edit
                  types.ts    short names for generated types
                  errors.ts   ApiError → translated message; query-client.ts retry policy
src/auth/         AuthProvider (page-load check, login, logout), RequireRole, Login
src/features/     teacher/ (dashboard, roster, student detail, payments) and parent/ (portal);
                  each feature's api/ holds only React Query hooks
src/components/   Sidebar, QueryState (loading / error / empty, used by every page)
src/lib/dates.ts  local-time dates (never the UTC day)
src/test/         fake API at the fetch boundary, fixtures, render helpers
nginx/            production server config (template) and its start-up check
Dockerfile        dev target (Vite) and prod target (nginx)
```

## Run it

```bash
npm ci
VITE_API_BASE_URL=http://localhost:8000/api/v1 npm run dev     # http://localhost:5173
```

The backend must allow the origin: `CORS_ALLOWED_ORIGINS=http://localhost:5173`. Create an
account from the portal's sign-up page, or with the backend's `manage.py create_teacher`.

## Checks (the same run in CI)

```bash
npm run typecheck
npm run lint            # oxlint, warnings are errors
npm run format:check    # Prettier
npm test                # Vitest, TZ=Europe/Rome
npm run build
npm run api:check       # generated types == what ../backend/openapi.yaml produces
```

When the backend contract changes: `npm run api:types`, fix what the compiler reports, commit.

## Session and security choices

- **Tokens.** The API issues a 15-minute access token and a 14-day refresh token that rotates
  on every use (the old one is blacklisted). The access token lives only in memory. The refresh
  token is stored in `localStorage`: this is an **accepted risk** (readable by an injected
  script), recorded in `docs/learning/adr/ADR-023-*`, with an httpOnly cookie as the next step.
- **Renewal.** One refresh at a time: concurrent 401s share one promise, and browser tabs take a
  Web Lock and re-read the stored token, so two renewals never race on a rotated token.
- **Logout** calls the API (`POST /api/v1/auth/logout/`) and clears every cached response.
- **Permissions** are enforced by the API; the SPA only routes for convenience and shows
  403/404 as messages.
- **Deployment** (`docs/learning/adr/ADR-025-*`): non-root nginx, no published host port (Coolify
  routes the domain), strict Content-Security-Policy (`script-src 'self'`, `connect-src` limited
  to the API origin, `frame-ancestors 'none'`), `nosniff`, `Referrer-Policy`,
  `Permissions-Policy`. The container refuses to start without a valid `API_ORIGIN`. CI builds
  and runs the image and checks these headers.

## Deploy (Coolify)

Service `web` in `../docker-compose.coolify.yml`. Set `API_PUBLIC_URL` (the API's public HTTPS
origin) and the service domain with the `:8080` suffix. Details: `../docs/operations/runbook.md`.
