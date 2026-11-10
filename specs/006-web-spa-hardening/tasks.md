# Tasks: Web Portal Hardening (Web 1)

**Input**: `specs/006-web-spa-hardening/` · **Tests**: REQUIRED · **Docs/ADR**: REQUIRED ·
👤 = needs the owner

## Phase 1: Setup

- [X] T001 Scripts in `frontend/package.json`: `typecheck` (tsc -b), `lint` (oxlint), `api:types` (pinned npx openapi-typescript from `../backend/openapi.yaml` to `src/api/schema.d.ts`), `api:check` (regenerate + `git diff --exit-code`); generate the schema; Vitest `TZ=Europe/Rome`
- [X] T002 Test helpers: `frontend/src/test/fake-api.ts` (fetch fake with route table and call log), extend `src/test/utils.tsx` (fresh QueryClient, auth, router)

## Phase 2: Foundational

- [X] T003 `frontend/src/api/types.ts` (aliases from the schema) and `src/lib/dates.ts` (`localDateISO`, `formatDay`, `formatDateTime`) + tests
- [X] T004 `frontend/src/api/client.ts`: `ApiError` (status 0 offline), base URL, access token in memory, refresh token in `localStorage` (`musicstudio.refresh`, legacy keys removed), single-flight refresh with Web Lock fallback, rotated token stored, `onExpired`, 401 → refresh → retry once, `fetchAllPages`
- [X] T005 Tests `frontend/src/api/client.test.ts`: bearer; rotation stored; three concurrent 401 → one refresh; refused refresh clears + notifies; offline keeps session; field errors parsed; login 401 does not refresh; `fetchAllPages` follows absolute `next`
- [X] T006 `frontend/src/api/errors.ts` + i18n keys (en/it) + tests; `src/api/query-client.ts` (no retry for 4xx/mutations); `src/components/QueryState.tsx` (loading/error+retry/empty)

## Phase 3: US1 — Session (P1) 🎯

- [X] T007 [US1] `frontend/src/auth/AuthProvider.tsx`: startup `/auth/me/` (offline → "unreachable" state with retry), login (token → me → `queryClient.clear()`), logout (server, retry on 400 with re-read token, always local clear + `queryClient.clear()`), session-expired notice; move `useAuth` export to keep oxlint clean
- [X] T008 [P] [US1] Tests `frontend/src/auth/session.test.tsx`: role routing after startup; offline keeps session; expired session → login with message; logout posts refresh and clears; logout after rotation sends the newest token; no previous user's data after re-login
- [X] T009 [US1] Login page: invalid credentials vs offline vs throttled messages; notice banner; `autocomplete` attributes

## Phase 4: US3 — Data and errors (P2)

- [X] T010 [US3] Feature API modules on generated types and the new client (dashboard, students all pages, student, student lessons, payments all pages / `?student=`, complete lesson, register payment) — remove hand-written response interfaces
- [X] T011 [US3] Pages with `QueryState`, translated enums, local dates, errors kept next to forms (Dashboard, Roster, StudentDetail, Payments, LessonCompleteModal, ParentPortal)
- [X] T012 [P] [US3] Tests per page: data / empty / error states; 30 students over two pages; 409 in the complete dialog; 400 on payment keeps the form; payment at 00:30 Rome carries the local date; parent portal read-only

## Phase 5: US2 — Safe deployment (P1)

- [X] T013 [US2] `frontend/nginx/default.conf.template` (fallback, cache rules, `/healthz`, `server_tokens off`, security headers with `${API_ORIGIN}` in CSP)
- [X] T014 [US2] `infra/frontend.Dockerfile` prod target: pinned node build, pinned `nginx-unprivileged`, `VITE_API_BASE_URL` build arg, template copied, port 8080; `.dockerignore`
- [X] T015 [US2] `docker-compose.coolify.yml`: `web` service (build args, `API_ORIGIN`, `expose`, healthcheck, depends on backend), backend `CORS_ALLOWED_ORIGINS` default to the web URL; `.env.example` (`API_PUBLIC_URL`); runbook section
- [ ] T016 [US2] Verify: no `ports:` in the Coolify compose; if Docker works in WSL, build and run the image and check uid, headers, fallback, health; record results
- [ ] T017 [US2] 👤 Deploy on Coolify and have the friend review

## Phase 6: US4 — Review readiness (P2)

- [X] T018 [US4] `frontend` job in `.github/workflows/ci.yml` (npm ci, typecheck, lint, test, build, api:check)
- [X] T019 [US4] oxlint 0 findings; page title; `frontend/README.md` rewritten (what, run, test, deploy, security choices)
- [X] T020 [US4] End-to-end: production build against local Django (login, roster, payment, logout + old refresh refused) — record in `docs/learning/verifica-web-end-to-end.md`

## Phase 7: US5 — Docs (P3)

- [ ] T021 [US5] ADR-023 (session, refresh in localStorage accepted risk, cookie next), ADR-024 (generated types), ADR-025 (container and headers)
- [ ] T022 [US5] Concept docs: `sicurezza-di-una-spa.md` (XSS, CSP, token storage), `deploy-di-una-spa-con-nginx.md`; OWASP walk updated for the SPA; glossary; Q&A; overview; `00-indice.md` ("Riepilogo Web 1")

## Phase 8: Polish

- [ ] T023 Full gate (backend + frontend) green; tasks marked; CLAUDE.md status
- [ ] T024 Export (`Web 1 - Portale` in `scripts/export-study-docs.sh`), vault decisions, summary commit

## Dependencies

T001–T002 → T003–T006 → US1 → US3 → US2 (container builds the finished SPA) → US4 → US5.

## Implementation strategy

MVP = US1 (users stop being logged out). Commit after each story.
