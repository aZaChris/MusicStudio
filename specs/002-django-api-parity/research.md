# Research: Mobile App on the Django API (Phase 1)

Sources: the inherited app (`src/`, read in full for the audit), the backend contract
`backend/openapi.yaml` at `2e32d55`, Expo SDK 57 tooling installed and tried locally
(`jest-expo` 57.0.6, `jest` 29.7, `@testing-library/react-native` 14.1, `openapi-typescript`
7.13.0 run via npx). Facts checked against the contract: login returns `{access, refresh}`;
refresh rotates (`{access, refresh}`); `POST /auth/logout/` takes `{refresh}` and answers 205;
errors are `{detail, code?}` or DRF field errors; lists are paginated (`count, next,
previous, results`, 25 per page); `GET /students/{id}/lessons/` returns a plain list (fixed in
the backend contract for this feature); payments can be filtered with `?student=`.

## 1. Where the app starts from — ADR-M001
- **Decision**: branch `refactor/mobile` from `app` (`3fb9be8`); `app` untouched.
- **Rationale**: same case-study shape as the backend (start from an existing commit, audit,
  refactor); UI, routing, theme and i18n are reusable; only the data layer is wrong.
- **Alternatives**: a fresh Expo project (no "before" to compare, re-does working UI); an app
  folder inside the backend branch (would mix two constitutions and toolchains).

## 2. Types from the contract — ADR-M002
- **Decision**: vendor the backend contract in `contract/openapi.yaml`; generate
  `src/lib/api/schema.d.ts` with `openapi-typescript@7.13.0` through `npx` (pinned); commit the
  output. `scripts/contract.mjs check` fails if the vendored file differs from
  `refactor/production-standards:backend/openapi.yaml` (git, origin first) or if regenerating
  the types gives a different file. `sync` refreshes both.
- **Rationale**: generated types make drift a compile error (the audit's camelCase types never
  matched Django). Running the generator via npx avoids its `typescript@^5` peer conflicting
  with the project's TypeScript 6.
- **Alternatives**: hand-written types (the bug we are fixing); `orval`/`openapi-generator`
  (generate whole clients and hooks — far more code than parity needs); a git submodule
  (heavy for one file).

## 3. HTTP client and session — ADR-M003
- **Decision**: keep a small own `apiFetch` in `src/lib/api/client.ts`, typed with the
  generated schemas. Access token kept **in memory**; refresh token in `expo-secure-store`
  (web: `localStorage`, dev only). On 401 the client calls `/auth/token/refresh/` once — a
  module-level promise makes concurrent 401s share one refresh — stores the rotated refresh,
  and retries the request once. If refresh fails, it clears the session and notifies the auth
  context (`onSessionExpired`). Logout posts the refresh token to `/auth/logout/`, then always
  clears storage and the React Query cache (`queryClient.clear()`).
- **Rationale**: the backend blacklists rotated refresh tokens, so two parallel refreshes would
  make the second fail and log the user out at random; single-flight avoids it. Keeping the
  15-minute access token only in memory means nothing long-lived but the refresh token is
  persisted.
- **Alternatives**: `openapi-fetch` with middleware (re-sending a consumed request body from a
  middleware is awkward; one more dependency for ~80 lines); `axios` interceptors (dependency;
  fetch is native); persisting the access token too (no benefit: it expires in 15 minutes).

## 4. Server state, errors and retries — ADR-M004
- **Decision**: TanStack Query stays. `QueryClient` default `retry`: never for `ApiError` with
  status < 500, at most 2 for network/5xx. `ApiError` carries status and a user message built
  from the body (`detail`, or the first field error), shown through translated templates
  ("Not allowed", "Not found", "Rejected by the server: …"). A `<QueryState>` component renders
  loading / error / empty uniformly.
- **Pagination**: `fetchAllPages(path)` follows `next` until null. Bounded by the product
  (1–10 teachers, ~300 students for a studio owner); marked with a `ponytail:` comment and the
  upgrade path (`useInfiniteQuery` with `onEndReached`).
- **Rationale**: retrying a 401/403/404/409 cannot succeed and delays the message; one error
  component keeps every screen honest about failures.

## 5. Dates
- **Decision**: `localDateISO(date)` builds `YYYY-MM-DD` from local `getFullYear/Month/Date`;
  display uses `toLocaleString` with the app locale. Never `toISOString().slice(0, 10)`.
- **Rationale**: audit issue 7 (UTC date after midnight in Italy). Unit-tested with a fixed
  time zone (`TZ=Europe/Rome` in Jest config).

## 6. Tests — ADR-M005
- **Decision**: `jest-expo` preset, React Native Testing Library, `global.fetch` replaced by a
  small fake router in `src/test/fake-api.ts`; `expo-secure-store` mocked by an in-memory map.
  Logic tests for the client/session/dates/errors; screen tests for loading, empty, error and
  data states of home, roster, detail, payments, portal and login.
- **Rationale**: the network boundary is the contract; mocking there tests our own code paths
  (refresh, error mapping) instead of mocking them away.
- **Alternatives**: MSW (another dependency and polyfills in RN Jest for a dozen routes);
  Detox/Maestro end-to-end (need emulators, unavailable here).

## 7. CI
- **Decision**: `.github/workflows/mobile-ci.yml` on pushes to `refactor/mobile`: `npm ci`,
  `tsc --noEmit`, `expo lint`, `jest --ci`, `contract:check` (checkout with full history so
  the backend branch is available as `origin/refactor/production-standards`).

## 8. Verification without emulators
- **Decision**: besides Jest, an end-to-end check of the web build against the local Django
  backend (dev settings, seeded demo data, `CORS_ALLOWED_ORIGINS` for the web origin), driven
  by the Playwright already present in devDependencies (`scripts/verify-web*.mjs` pattern).
  Real iOS/Android runs are an owner task.

## 9. Small decisions
- Logout is in the header of every role's area (teacher tabs and parent portal).
- Parent portal reads payments with `?student=<id>` instead of filtering a full list.
- Tab icons keep the text glyphs but get `accessibilityLabel`s; `@expo/vector-icons` is not
  added (parity, no new dependency).
- Lint error in `use-color-scheme.web.ts`: replaced with `useSyncExternalStore`-free version
  based on the Expo template's current recommendation, or the rule suppressed with a reason if
  the hydration pattern is required; decided at implementation, recorded in the commit.
