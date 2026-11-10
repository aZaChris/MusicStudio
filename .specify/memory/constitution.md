<!--
Sync Impact Report
Version change: 3.0.0 → 3.0.1 (PATCH: work moved to staging/mobile, backend on staging/backend,
  old branches archived as tags; no principle changed)

Previous report (3.0.0):
Version change: 2.0.0 → 3.0.0 (MAJOR: the repository is redefined from the Next.js web platform
  to the mobile client only; every principle is redefined for a client of the Django API)
Modified principles:
  I. Tenant Isolation & RBAC → I. The Backend Is the Security Authority
  II. API-First Architecture → II. Contract-Driven API Client
  III. Test-First on Core Business Logic → IV. Tested Features
  IV. MVP Scope Discipline → V. Phased Scope Discipline
  V. Production-Quality Codebase → VII. Automated Quality Gate (+ parts of II)
  VI. Bilingual & Themeable UI → VI. Accessible, Bilingual, Themed UI
Added principles: III. Secure Session Handling; VIII. Decisions & Study Docs Ship With Code;
  IX. Security Verified Per Phase (OWASP Mobile Top 10)
Removed sections: Next.js/Drizzle/Neon/Auth.js/Vercel stack constraints (server code no longer
  lives here; the backend is the Django API on branch staging/backend)
Templates requiring updates:
  ✅ .specify/templates/plan-template.md (Constitution Check gates listed)
  ✅ .specify/templates/spec-template.md (generic, compatible as-is)
  ✅ .specify/templates/tasks-template.md (generic; tests are mandatory per Principle IV and are
     generated as such by /speckit-tasks for this project)
  ✅ README.md (rewritten for the mobile app in feature 002)
Follow-up TODOs: none
-->

# MusicStudio Mobile Constitution

## Core Principles

### I. The Backend Is the Security Authority (NON-NEGOTIABLE)
Tenant isolation, roles and permissions are enforced by the Django API, never by the app. The
app MUST NOT infer access from what it has cached or from the user's role alone: it shows what
the server returns and handles every refusal explicitly — 401 (session expired: refresh, then
back to login), 403 (not allowed: message, no retry), 404 (not visible: "not found", never a
crash). On logout or account switch the app MUST clear every cached response, so no data of
one user is ever shown to the next.
Rationale: hiding a button is not security; the server already proves cross-tenant denial with
tests, and the app must not create a second, weaker source of truth.

### II. Contract-Driven API Client
Response and request types MUST be generated from the backend's OpenAPI contract
(`backend/openapi.yaml` on branch `staging/backend`), vendored into this
repository. A check MUST fail when the vendored copy differs from the backend branch.
Hand-written response types are forbidden; screens consume the generated types through a thin
typed client in `src/lib/`.
Rationale: hand-written types silently drift from the server (the inherited app used camelCase
fields the Django API never sends); generated types turn drift into a compile error.

### III. Secure Session Handling
Tokens MUST live only in `expo-secure-store` on native platforms (the web fallback exists for
local development only). The access token is refreshed with the rotating refresh token on a
401, with a single in-flight refresh shared by concurrent requests. Logout MUST call
`POST /api/v1/auth/logout/` before clearing local state, and still clear local state if the
call fails. Tokens and passwords MUST never be logged or put in URLs.
Rationale: the backend revokes refresh tokens (rotation + blacklist); a client that ignores
rotation logs users out at random, and a local-only logout leaves a valid token behind.

### IV. Tested Features
Every feature ships automated tests in the same change: Jest with `jest-expo` and React Native
Testing Library. Tested at minimum: the API client and session logic (refresh, logout, error
mapping), and for each main screen its loading, empty, error and data states. Tests mock the
network at the `fetch` boundary, not internal modules.
Rationale: the inherited app had no tests at all; session and money screens are where silent
bugs cost trust.

### V. Phased Scope Discipline
Phase 1 is parity with the old `app` branch (tag `archive/app`) on the Django API (login/logout, teacher home, roster
and student detail, complete lesson, payments, parent portal). New features need a spec.
Native modules that require a custom development build are out of scope unless decided in an
ADR: the app MUST keep running in Expo Go. Stripe, if ever used, is test mode only.
Rationale: a client rewrite dies of scope creep exactly like a backend does.

### VI. Accessible, Bilingual, Themed UI
All user-facing text goes through the typed EN/IT dictionary; enum values from the API are
translated, never shown raw. Light and dark themes are supported. Interactive elements declare
an accessibility role and label. Dates and times are shown and computed in the device's time
zone — never by slicing UTC ISO strings for a local date.
Rationale: product requirement since the MVP; the UTC date slice already produced wrong
payment dates after midnight in Italy.

### VII. Automated Quality Gate
A GitHub Actions workflow MUST run on every push to this branch: TypeScript (`tsc --noEmit`,
strict), ESLint, Jest, and the contract drift check. The same commands run locally before
commit. A red pipeline blocks merge.
Rationale: standards not enforced by a machine erode.

### VIII. Decisions & Study Docs Ship With Code
Every non-trivial decision produces an ADR in `docs/learning/adr/` (context, decision, rejected
alternatives, consequences). Every feature produces Italian study documentation in
`docs/learning/` in the same format as the backend (concept docs of 800–1500 words, glossary,
interview Q&A, index). Code, comments, identifiers and commits are in English; study docs are
in Italian; commit bodies explain why.
Rationale: the project trains its developer; undocumented decisions cannot be defended.

### IX. Security Verified Per Phase
At the end of every phase the OWASP Mobile Top 10 is walked against the app and the result is
recorded in `docs/learning/` (covered, partial, accepted, with evidence). No secrets in the
repository: the app bundle is public by nature, so only public configuration (the API base URL)
lives in `EXPO_PUBLIC_*` variables.
Rationale: security reviewed once at the end is security never reviewed.

## Additional Constraints

- **Stack**: Expo SDK 57, Expo Router (typed routes), React Native, TypeScript strict,
  TanStack Query for server state, `expo-secure-store` for tokens. Dependencies are added with
  `npx expo install` so versions match the SDK; Expo's versioned docs for v57 are the reference.
- **Backend**: the Django REST API on branch `staging/backend`, base path
  `/api/v1/`, configured through `EXPO_PUBLIC_API_BASE_URL`. No AWS services.
- **Branches**: work happens on `staging/mobile`. The old `app` and `web` branches are archived
  as tags `archive/app` and `archive/web`, which are never moved.

## Development Workflow

- Features flow through spec-kit: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. Ad-hoc work beyond trivial fixes is discouraged.
- Small commits on `staging/mobile`; each completed phase ends with a summary commit and an
  updated `docs/learning/00-indice.md`.
- Ambiguous choices that significantly change the architecture: pick the simplest, most
  conservative option, record it in an ADR, and continue.

## Governance

This constitution supersedes ad-hoc practices when they conflict. Amendments go through
`/speckit-constitution`, require a stated rationale, and bump the version per semantic
versioning (MAJOR: principle removed or redefined incompatibly; MINOR: principle added or
materially expanded; PATCH: wording). Every change is self-reviewed against Principles I, II
and III; violations are fixed or justified in the plan's Complexity Tracking before merge.

**Version**: 3.0.1 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-11-10
