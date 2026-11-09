# MusicStudio — mobile app

The Expo (React Native) client of MusicStudio, a platform for private music teachers and small
studios: lessons, lesson packages, payments, and a read-only portal for parents.

This branch, `refactor/mobile`, is a refactor case study: it starts from branch `app` (an Expo
app written for a Next.js API) and rewires it onto the **Django REST API** of branch
`refactor/production-standards`, with production standards (generated API types, real session
handling, tests, CI). The starting point and its problems are in
[`docs/learning/audit-iniziale.md`](docs/learning/audit-iniziale.md); principles in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md); the current feature in
[`specs/002-django-api-parity/`](specs/002-django-api-parity/).

## Stack

- Expo SDK 57, Expo Router (typed routes), React Native 0.86, TypeScript strict
- TanStack Query for server state; `expo-secure-store` for the refresh token
- Types generated from the backend OpenAPI contract (`contract/openapi.yaml`)
- Jest (`jest-expo`) + React Native Testing Library; GitHub Actions

## What the app does

- **Teachers and studio owners**: home with active students, pending payments, upcoming lessons
  and low-package warnings; complete a lesson with a note; roster and student detail; payments
  list and manual payment registration.
- **Parents**: read-only portal per child — lessons, attendance, payments.
- **Everyone**: sign in, silent session renewal, sign out that ends the session on the server.

## Layout

```text
src/app/          screens (Expo Router): login, (teacher)/…, (parent)/portal
src/lib/api/      client.ts (fetch, ApiError, single-flight refresh, pagination),
                  schema.d.ts (generated — do not edit), types.ts (short names)
src/lib/          auth-context, queries (React Query hooks), errors, dates, i18n
src/components/   Button, Card, TextField, QueryState, LessonCompleteModal, LogoutButton
src/test/         fake API at the fetch boundary, fixtures, render helpers
contract/         vendored backend contract
scripts/          contract.mjs (sync/check), verify-django.mjs (end-to-end on the web build)
docs/learning/    Italian study docs (audit, ADR, concepts, Q&A)
```

## Run it

```bash
npm ci
cp .env.example .env            # set EXPO_PUBLIC_API_BASE_URL to your backend
npx expo start                  # Expo Go on a phone, or press w for the web
```

The backend runs from branch `refactor/production-standards` (see its `CLAUDE.md`); for the web
build allow the origin with `CORS_ALLOWED_ORIGINS=http://localhost:8081`. Demo accounts come
from its `manage.py seed_demo` (password `password123`).

## Quality gate

```bash
npx tsc --noEmit
npx expo lint
npm test
npm run contract:check      # contract == backend branch, types == generator output
```

When the backend contract changes: `npm run contract:sync`, fix what the compiler reports,
commit both files.
