# Tasks: Mobile App on the Django API (Phase 1, Parity)

**Input**: `specs/002-django-api-parity/` · **Tests**: REQUIRED (constitution IV) ·
**Docs/ADR**: REQUIRED (constitution VIII) · 👤 = needs the owner (real device)

## Phase 1: Setup

- [X] T001 Test tooling as devDependencies (`jest`, `jest-expo`, `@types/jest`, `@testing-library/react-native`), scripts `test`, `typecheck`, `contract:sync`, `contract:check`, Jest preset + `TZ=Europe/Rome` in `package.json`; remove the smoke test once real tests exist
- [X] T002 Vendor `contract/openapi.yaml` and write `scripts/contract.mjs` (`sync`: copy from `refactor/production-standards:backend/openapi.yaml`, origin first, and regenerate `src/lib/api/schema.d.ts` with `npx openapi-typescript@7.13.0`; `check`: fail on drift of either file)
- [X] T003 Test helpers: `src/test/fake-api.ts` (route table → Response, call log), `src/test/setup.ts` (in-memory `expo-secure-store` mock, fetch reset), `src/test/render.tsx` (providers: QueryClient without retries, locale, auth)

## Phase 2: Foundational

- [X] T004 `src/lib/api/types.ts` aliases from the generated schema (Me, Lesson, Student, Package, Payment, Dashboard, LowPackageStudent, enums)
- [X] T005 `src/lib/dates.ts` (`localDateISO`, `formatDateTime`, `formatDate`) + tests in `src/lib/__tests__/dates.test.ts` (00:30 Rome → local date, not UTC)
- [X] T006 `src/lib/api/client.ts`: `apiFetch`, `ApiError` (status, code, detail, fieldErrors; status 0 for network), base URL from `EXPO_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api/v1`), trailing-slash paths, `fetchAllPages`
- [X] T007 `src/lib/session.ts`: refresh token in secure storage, access token in memory, single-flight `refreshAccess()`, `onSessionExpired` listener; wired into `apiFetch` (401 → refresh → retry once)
- [X] T008 Tests `src/lib/__tests__/client.test.ts`: bearer header; 401 → one refresh → retry; three concurrent 401s → exactly one refresh call; rotated refresh stored; refresh failure → session cleared + listener called; network error → status 0; `fetchAllPages` follows `next`
- [X] T009 `src/lib/errors.ts` (ApiError → translated message: network, 401, 403, 404, 409/400 with server detail or first field error, 429, 5xx) + i18n keys in `src/lib/i18n.ts` + tests `src/lib/__tests__/errors.test.ts`
- [X] T010 `src/components/QueryState.tsx` (loading / error with retry button / empty) and QueryClient policy in `src/lib/query-client.ts` (no retry for ApiError < 500, max 2 otherwise)

## Phase 3: US1 — Sign in, renew, sign out (P1) 🎯

- [X] T011 [US1] `src/lib/auth-context.tsx`: login (`/auth/token/` then `/auth/me/`), startup (`/auth/me/` if a refresh token exists), logout (`/auth/logout/` best effort → clear storage → `queryClient.clear()`), expired-session state with message
- [X] T012 [P] [US1] Tests `src/lib/__tests__/auth-context.test.tsx`: login ok per role; wrong credentials → error and nothing stored; startup re-verifies; logout posts refresh and clears cache even if server fails; expired session → signed out with reason
- [X] T013 [US1] `src/app/login.tsx` on the new auth (expired-session banner, network vs invalid credentials messages, a11y); `src/app/index.tsx` routing by verified role
- [X] T014 [P] [US1] Screen test `src/app/__tests__/login.test.tsx` (invalid credentials message, success navigates)

## Phase 4: US2 — Teacher home + complete lesson (P1)

- [X] T015 [US2] `src/lib/queries.ts` rewritten on the client and generated types (dashboard, students all pages, student, student lessons, payments, complete lesson, register payment; invalidations per data-model)
- [X] T016 [US2] `src/app/(teacher)/home.tsx` (QueryState, empty upcoming, local date/time, low-package card) + logout in the teacher header (`src/app/(teacher)/_layout.tsx`, a11y labels on tabs)
- [X] T017 [US2] `src/components/LessonCompleteModal.tsx`: server error shown inside the dialog, dialog stays open on failure
- [X] T018 [P] [US2] Tests `src/app/__tests__/home.test.tsx`: data, empty, error states; completing a lesson posts the note and refreshes; 409 shown in the dialog

## Phase 5: US3 — Roster + student detail (P2)

- [X] T019 [US3] `src/app/(teacher)/roster/index.tsx` (all pages, translated payment status, a11y) and `roster/[id].tsx` (package with translated status, "Lessons" history title, 404 → not-found state)
- [X] T020 [P] [US3] Tests `src/app/__tests__/roster.test.tsx`: 30 students over two pages all shown; detail data; detail 404

## Phase 6: US4 — Payments (P2)

- [X] T021 [US4] `src/app/(teacher)/payments.tsx`: all students in the picker, translated methods and statuses, local date, field errors shown, form kept on error, reset on success
- [X] T022 [P] [US4] Tests `src/app/__tests__/payments.test.tsx`: posts local date (fake clock 00:30 Rome), 400 amount error shown and form kept, success resets

## Phase 7: US5 — Parent portal (P2)

- [X] T023 [US5] `src/app/(parent)/portal.tsx`: child selector, lessons via `/students/{id}/lessons/`, payments via `?student=`, translated statuses, no write actions, logout
- [X] T024 [P] [US5] Tests `src/app/__tests__/portal.test.tsx`: two children switch, no children message, payments requested with `student` filter, no write controls

## Phase 8: US6 — Quality gate and study docs (P3)

- [X] T025 [US6] Fix the lint error in `src/hooks/use-color-scheme.web.ts`; `npx expo lint` clean
- [X] T026 [US6] `.github/workflows/mobile-ci.yml` (npm ci, tsc, lint, jest --ci, contract:check with full history)
- [X] T027 [US6] `scripts/verify-django.mjs`: Playwright against the exported web build and the local Django backend (login owner, home counts, complete lesson, payment, logout + old refresh refused, parent portal); run it and record the output in `docs/learning/verifica-end-to-end.md`
- [ ] T028 [US6] ADRs `docs/learning/adr/ADR-M001…M005`, concept docs (800–1500 words): `client-api-generato-dal-contratto.md`, `sessione-jwt-nel-client.md`, `stato-del-server-con-react-query.md`, `test-di-un-app-react-native.md`; glossary, interview Q&A, `00-indice.md`, OWASP Mobile Top 10 walk `concetti/sicurezza-mobile-owasp.md`
- [X] T029 [US6] Rewrite `README.md` for the mobile app; `.env.example` with `EXPO_PUBLIC_API_BASE_URL`

## Phase 9: Polish

- [ ] T030 Full gate green (tsc, lint, jest, contract check); tasks marked; CLAUDE.md status
- [ ] T031 Export the mobile study docs for NotebookLM (folder `Mobile - Fase 1`), vault decisions, phase summary commit
- [ ] T032 👤 Run the app in Expo Go on a real phone against a reachable backend

## Dependencies

T001–T003 → T004–T010 → US1 → US2..US5 (independent of each other, all need T015 which
lives in US2: do it first) → US6 → Polish. T032 does not block closing the phase.

## Parallel opportunities

Screen test files ([P]) can be written alongside their screens; concept docs in parallel.

## Implementation strategy

MVP = Foundational + US1 (the app can sign in to Django and stay signed in). Then screens in
priority order, committing after each story.
