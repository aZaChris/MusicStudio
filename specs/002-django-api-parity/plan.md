# Implementation Plan: Mobile App on the Django API (Phase 1, Parity)

**Branch**: `refactor/mobile` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-django-api-parity/spec.md`

## Summary

Replace the inherited data layer (single token from a Next.js API, hand-written camelCase
types) with a client of the Django API: types generated from the vendored OpenAPI contract, a
small `apiFetch` with single-flight refresh on 401 and server logout, a React Query policy that
never retries 4xx and shows translated errors. Port the existing screens to the new shapes at
parity, fix the audit's medium and minor issues (all pages of students, local dates,
translated enums, accessibility labels, logout for every role, startup `/auth/me/`), add Jest
tests and CI, and write the Italian study docs. Decisions in [research.md](research.md),
ADR-M001…M005.

## Technical Context

**Language/Version**: TypeScript 6 (strict), React 19.2, React Native 0.86, Expo SDK 57

**Primary Dependencies**: expo-router, @tanstack/react-query, expo-secure-store,
expo-localization (all existing). Dev: jest 29.7, jest-expo 57, @testing-library/react-native
14. `openapi-typescript@7.13.0` run through npx only (not a project dependency).

**Storage**: refresh token in expo-secure-store (Keychain/Keystore); web dev fallback
localStorage. No local database.

**Testing**: Jest + RNTL with a fake `fetch`; Playwright against the web build and a local
Django backend for end-to-end checks.

**Target Platform**: iOS and Android via Expo Go; web build for development verification.

**Project Type**: mobile app (client of a REST API).

**Performance Goals**: screens usable on a mid-range phone; at most one token refresh per
expiry; roster of ~300 students (studio owner) loads in a handful of requests.

**Constraints**: runs in Expo Go (no custom native modules); backend contract is the source of
truth; no secrets in the bundle.

**Scale/Scope**: 8 routes (login, teacher home, roster, student detail, payments, parent
portal, index redirect, layouts), ~25 source files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] I. Server is the authority: 401 → refresh → login; 403/404 explicit states; `clear()` on
  logout.
- [X] II. Types generated from `contract/openapi.yaml`; `contract:check` compares with the
  backend branch and regenerates.
- [X] III. Refresh in secure storage, access in memory, single-flight refresh, server logout.
- [X] IV. Tests for client/session/dates/errors and for screen states of every main screen.
- [X] V. Parity only; Expo Go only; no Stripe.
- [X] VI. Typed EN/IT; enums translated; a11y roles/labels; local dates.
- [X] VII. GitHub Actions: tsc, lint, jest, contract check.
- [X] VIII. ADR-M001…M005; concept docs; glossary, Q&A, index.
- [X] IX. OWASP Mobile Top 10 walk at the end of the phase.

Post-design re-check: passing; Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-django-api-parity/
├── plan.md  research.md  data-model.md  quickstart.md
├── contracts/api-usage.md
└── tasks.md
```

### Source Code (repository root)

```text
contract/openapi.yaml            vendored backend contract
scripts/contract.mjs             sync | check (git show of the backend branch + regenerate)
scripts/verify-django.mjs        Playwright end-to-end against web build + local Django
src/lib/api/schema.d.ts          generated (do not edit)
src/lib/api/client.ts            apiFetch, ApiError, single-flight refresh, fetchAllPages
src/lib/api/types.ts             aliases: Lesson, Student, Payment, Dashboard, Me (from schema)
src/lib/session.ts               token storage (secure-store), session events
src/lib/auth-context.tsx         login/logout/startup /auth/me, expired-session handling
src/lib/queries.ts               hooks on the new client and shapes
src/lib/errors.ts                ApiError → translated message
src/lib/dates.ts                 localDateISO, formatters
src/lib/i18n.ts                  + enum and error keys
src/components/QueryState.tsx    loading / error / empty
src/app/**                       screens ported to snake_case shapes; logout in teacher header
src/test/                        fake-api.ts, render helpers; jest setup (secure-store mock, TZ)
.github/workflows/mobile-ci.yml
docs/learning/                   Italian study docs (ADR-M00x, concetti, glossario, Q&A, indice)
README.md                        rewritten for the mobile app
```

**Structure Decision**: single Expo project; `src/lib/api/` isolates everything that knows
about HTTP and the contract, screens only use hooks.

## Implementation order

1. Contract vendoring + generated types + contract script (US6 groundwork).
2. Client, session, auth context, errors, dates — with tests (US1).
3. Screens: home + complete lesson (US2), roster + detail (US3), payments (US4), portal (US5),
   each with screen-state tests.
4. Lint fix, a11y, i18n of enums; CI workflow.
5. End-to-end web check against the local Django backend.
6. Study docs, OWASP Mobile walk, README, export.

## Complexity Tracking

No violations.
