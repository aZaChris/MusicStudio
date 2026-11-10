# Quickstart: validating Web 1

1. `cd frontend && npm ci`
2. Gate: `npx tsc -b && npx oxlint && npx vitest run && npx vite build && npm run api:check`
   — all green, oxlint with 0 findings.
3. Contract drift: edit a field in `../backend/openapi.yaml` (no commit) → `npm run api:check`
   fails; restore → passes.
4. Session (tests): rotated refresh stored; three concurrent 401s → one refresh; logout after a
   rotation sends the newest token; cache empty after logout.
5. Container (Docker): `docker build -f infra/frontend.Dockerfile --target prod
   --build-arg VITE_API_BASE_URL=https://api.example.com/api/v1 -t musicstudio-web frontend`;
   `docker run --rm -e API_ORIGIN=https://api.example.com -p 18080:8080 musicstudio-web`
   (host port only for the local check); `curl -I localhost:18080/students` → 200 + headers;
   `docker run --rm musicstudio-web id -u` → 101; `/healthz` → ok.
6. Compose review: `grep -n "ports:" docker-compose.coolify.yml` → no matches.
7. End-to-end: production build against the local Django (dev settings, in-memory cache,
   `CORS_ALLOWED_ORIGINS` = the SPA origin): login, roster, payment, logout + old refresh 401.
