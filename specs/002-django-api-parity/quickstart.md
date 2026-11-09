# Quickstart: validating mobile phase 1

1. `npm ci`
2. Gate: `npx tsc --noEmit && npx expo lint && npm test && npm run contract:check` — all green.
3. Contract drift: edit one line of `contract/openapi.yaml` → `npm run contract:check` fails;
   `git checkout contract/` → passes again.
4. Local backend (main checkout, `backend/`): PostgreSQL running, `DATABASE_URL` set,
   `CORS_ALLOWED_ORIGINS=http://localhost:8081`, `uv run python manage.py migrate`,
   `uv run python manage.py seed_demo`, `uv run python manage.py runserver 8000`
   (dev settings).
5. App on the web: `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npx expo start --web`.
   - Sign in as `owner@example.com` / `password123` → teacher home with the seeded counts.
   - Complete the seeded lesson with a note → upcoming list and remaining lessons update.
   - Roster → student detail shows lesson history.
   - Register a cash payment → appears with today's local date.
   - Log out → login screen; the old refresh token is refused by the server.
   - Sign in as `parent@example.com` → portal, read-only, only the linked child.
6. Automated web check: `node scripts/verify-django.mjs` (Playwright) runs the steps above
   against the exported web build and prints PASS/FAIL per step.
7. Owner: run in Expo Go on a real phone against a reachable backend.
