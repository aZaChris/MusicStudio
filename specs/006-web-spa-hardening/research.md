# Research: Web Portal Hardening (Web 1)

Sources: `frontend/src` read in full for the audit (`docs/learning/audit-frontend.md`); the
mobile refactor on branch `refactor/mobile` (same API, same session problems, solutions tested
there: ADR-M002…M005); backend ADR-018 (rotation + blacklist) and ADR-021 (client IP behind one
proxy); `docker-compose.coolify.yml`; `infra/frontend.Dockerfile`.

## 1. Session — ADR-023
- **Decision**: port the mobile client's session model to the SPA. Access token in memory;
  refresh token in `localStorage` (owner decision, accepted risk); after every refresh store the
  rotated refresh token; one refresh in flight per tab (shared promise) and across tabs (Web
  Locks API `navigator.locks.request`, re-reading the stored token inside the lock, plain call
  where the API is missing); on refused refresh clear and notify the auth context; logout
  posts `/auth/logout/`, retries once with the re-read token on 400 (rotation just before),
  then always clears storage and `queryClient.clear()`; startup `/auth/me/`, offline keeps the
  session.
- **Why**: fixes audit issues 1–3 with code already proven by tests on mobile; the cross-tab
  lock is the web-specific addition (two tabs share one `localStorage`).
- **Rejected**: httpOnly cookie now (needs backend endpoints, CSRF, CORS with credentials —
  next step, recorded in ADR-023); BroadcastChannel to sync tabs (more code than a lock);
  keeping the access token in `localStorage` (no benefit, more XSS exposure).

## 2. Contract types — ADR-024
- **Decision**: `openapi-typescript@7.13.0` through pinned `npx` (its typescript@5 peer clashes
  with the SPA's TypeScript 6), generating `src/api/schema.d.ts` from `../backend/openapi.yaml`
  (same branch: no vendored copy). `npm run api:check` regenerates and fails on `git diff`.
  `src/api/types.ts` gives short names. Feature `api/*.ts` modules keep only hooks.
- **Rejected**: vendoring (unneeded on the same branch); orval (generates far more code).

## 3. Data and errors
- **Decision**: `fetchAllPages` following DRF `next` (path + query only); `ApiError` with
  status (0 = offline), detail, code, field errors; `errorMessage()` through i18next keys;
  QueryClient: no retry for 4xx, max 2 for network/5xx, none for mutations; a `QueryState`
  component for loading / error with retry / empty; `localDateISO` for payment dates.
- **Why**: same fixes as mobile ADR-M004; bounded lists for 1–10 teachers (ponytail note).

## 4. Production container — ADR-025
- **Decision**: rework `infra/frontend.Dockerfile` (one file, `dev` target kept for the dev
  compose): build stage on a pinned `node:22.12.0-alpine`; runtime on
  `nginxinc/nginx-unprivileged:1.27.3-alpine` (non-root, listens on 8080). nginx config as a
  template (`envsubst` at start, built into the official image) with: SPA fallback
  (`try_files $uri /index.html`), long cache for hashed `/assets/`, no cache for
  `index.html`, `/healthz`, `server_tokens off`, and headers:
  `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self';
  img-src 'self' data:; font-src 'self'; connect-src 'self' ${API_ORIGIN};
  object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`,
  `X-Frame-Options: DENY` (old browsers), `Cross-Origin-Opener-Policy: same-origin`.
  HSTS is set by Coolify's proxy for the HTTPS domain, not by nginx behind it.
- **Compose**: new service `web` in `docker-compose.coolify.yml`, `expose: ["8080"]`, no
  `ports:`, healthcheck with busybox `wget`, build arg `VITE_API_BASE_URL` and runtime
  `API_ORIGIN` both from one required variable `API_PUBLIC_URL`; backend
  `CORS_ALLOWED_ORIGINS` defaults to the web service's Coolify URL.
- **Why same-origin proxying was rejected**: putting nginx in front of the API on the SPA's
  domain would add a second proxy hop for SPA traffic only; `TRUSTED_PROXY_COUNT` would be
  right for one path and wrong for the other, breaking the throttle identity fixed in phase 4.
  Separate origins + strict CORS keep one rule.
- **Rejected**: serving the SPA from Django/whitenoise (couples deploys, CSP per path);
  `nginx:alpine` as root; a Node static server (bigger, slower, more surface).

## 5. Verification
- Vitest + Testing Library with `fetch` faked at the boundary (port of the mobile fake API);
  session tests mirror the mobile ones (rotation stored, single flight, logout retry, cache
  cleared). Container: if Docker is available in WSL, build the image and check user, headers,
  fallback and health; otherwise `vite build` + review of the nginx template, recorded as such.
- CI job `frontend` in `.github/workflows/ci.yml`: `npm ci`, `tsc -b`, `oxlint`,
  `vitest run`, `vite build`, `npm run api:check`.
