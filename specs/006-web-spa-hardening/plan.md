# Implementation Plan: Web Portal Hardening (Web 1)

**Branch**: `refactor/production-standards` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-web-spa-hardening/spec.md`

## Summary

Bring the React SPA in `frontend/` up to the backend's standards. Session: rotated refresh
token stored, one refresh in flight (per tab and across tabs), access token in memory, server
logout, cache cleared, startup `/auth/me/`. Data: types generated from `backend/openapi.yaml`,
all pages, translated errors, no 4xx retries, local dates. Deployment: a non-root, pinned nginx
image with an SPA fallback and strict security headers, added to the Coolify compose with no
published ports and a strict CORS origin on the API. Quality: tests per screen state and for
the session, a CI job, README for the reviewer, Italian study docs. ADR-023…025.

## Technical Context

**Language/Version**: TypeScript 6 (strict), React 19, Vite 8

**Primary Dependencies**: existing (TanStack Query, react-router 7, i18next). Dev:
Vitest, Testing Library, oxlint (existing). `openapi-typescript@7.13.0` via pinned npx only.
Runtime image: `nginxinc/nginx-unprivileged:1.27.3-alpine`; build: `node:22.12.0-alpine`.

**Storage**: browser `localStorage` (refresh token, theme, language); memory (access token).

**Testing**: Vitest + jsdom + Testing Library, `fetch` faked at the boundary; container checks
with Docker if available in WSL.

**Target Platform**: modern browsers; container on Coolify behind its Traefik proxy.

**Project Type**: web SPA (client of the Django API in the same repository).

**Performance Goals**: initial bundle not larger than today's (374 kB, 116 kB gzip) by more
than 10%; hashed assets cached for a year.

**Constraints**: no published host ports; non-root container; CSP without `unsafe-inline` or
`unsafe-eval`; no secrets in the bundle (only `VITE_API_BASE_URL`); `web`/`app` branches
untouched.

**Scale/Scope**: 6 pages, ~1,400 lines.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] I. Tenant data untouched; the SPA shows what the scoped API returns; 403/404 explicit.
- [X] II. SPA consumes `/api/v1/`; types generated from the committed contract.
- [X] III. Tests in the same change (session + screen states); backend unchanged except CORS
  default in compose (no query budget impact).
- [X] IV. Hardening only; no new product features.
- [X] V. Backend layering untouched.
- [X] VI. Web client rules applied (generated types, rotating-token session, tests); `web`/`app`
  untouched.
- [X] VII. CI job for the SPA added.
- [X] VIII. ADR-023 (session + token storage risk), ADR-024 (generated types), ADR-025
  (container and headers); concept docs; index, glossary, Q&A.
- [X] IX. OWASP walk extended to the SPA (XSS, CSP, token storage, bundle contents).

Post-design re-check: passing; Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-web-spa-hardening/
├── plan.md  research.md  data-model.md  quickstart.md
├── contracts/deployment.md
└── tasks.md
```

### Source Code

```text
frontend/
├── src/api/schema.d.ts        generated (do not edit)
├── src/api/types.ts           short names for generated types
├── src/api/client.ts          apiFetch, ApiError, session (memory access, rotated refresh,
│                              single flight + Web Lock), fetchAllPages
├── src/api/errors.ts          ApiError → i18next message
├── src/api/query-client.ts    retry policy
├── src/auth/AuthProvider.tsx  startup /auth/me/, login, logout (server + retry), expiry
├── src/components/QueryState.tsx
├── src/lib/dates.ts           localDateISO, formatters
├── src/features/**            hooks on generated types; pages use QueryState
├── src/test/fake-api.ts       fetch fake (port of mobile)
├── package.json               scripts: api:types, api:check, typecheck, lint
├── README.md                  rewritten for the reviewer
└── nginx/default.conf.template
infra/frontend.Dockerfile      dev target kept; prod: pinned non-root nginx
docker-compose.coolify.yml     + `web` service (expose 8080, healthcheck), CORS default
.github/workflows/ci.yml       + `frontend` job
docs/learning/                 ADR-023…025, concept docs, OWASP update, index, glossary, Q&A
```

**Structure Decision**: keep the existing feature folders; centralise HTTP, session and
errors in `src/api/` so pages only use hooks.

## Implementation order

1. Generated types + `api:check` (foundation).
2. Client, session, errors, query policy, dates — with tests (US1, US3).
3. AuthProvider and pages ported; QueryState; all pages (US1, US3).
4. Container, nginx template, compose, CORS (US2) — verify with Docker if available.
5. CI job, lint clean, README (US4).
6. End-to-end against local Django; docs (US5); export.

## Complexity Tracking

No violations.
