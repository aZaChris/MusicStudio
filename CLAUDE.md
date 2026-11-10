# MusicStudio Mobile — working rules for Claude Code

Read this first in every session on this branch. Answer the user (Christian) **in Italian**:
he is a developer with ~1.5 years of experience, English B1, and studies everything built here.
Also read `AGENTS.md` (Expo SDK 57 docs are the reference: https://docs.expo.dev/versions/v57.0.0/).

## What this branch is

- `staging/mobile`: the Expo app, refactored onto the **Django REST API** of branch
  `staging/backend` (case study, like the backend refactor). It is a copy of `refactor/mobile`,
  which started from the old branch `app` (commit `3fb9be8`), written for the Next.js API of the
  old branch `web`. Both old branches are archived as tags `archive/app` and `archive/web`.
- The backend lives on its own branch; contract fixes go there, then the vendored contract here
  is refreshed (`npm run contract:sync`).
- Principles: `.specify/memory/constitution.md` (v3.0.0). Starting point:
  `docs/learning/audit-iniziale.md`.

## Status

| Phase | Feature dir | Status |
|---|---|---|
| 1 Parity on the Django API | `specs/002-django-api-parity` | code, docs, CI and local gate green; to close: real-device run in Expo Go (T032, owner) |

Open items: `docs/learning/00-indice.md` ("Aperto"); `expo-router` advisories in the bundle wait
for an SDK patch (`npx expo install --fix`), never `npm audit fix --force`.

## How to work

- Spec-kit per feature: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. `.specify/feature.json` points to the active feature.
- Autonomy until the phase is complete, then stop with an Italian summary. Ambiguous
  architectural choice: simplest conservative option + ADR.
- Commits: small, English, body explains *why*. Push only when the user asks.
- Code/comments/commits in English; study docs (`docs/learning/`) in Italian, same format as
  the backend (concept docs 800–1500 words, `wc -w`).
- Add dependencies with `npx expo install <pkg>` (SDK-matched versions).

## Quality gate

```bash
npm ci
npx tsc --noEmit
npx expo lint
npm test                      # jest-expo + React Native Testing Library
npm run contract:check        # vendored OpenAPI == backend branch
```

`npm run contract:sync` refreshes `contract/openapi.yaml` from the backend branch and
regenerates `src/lib/api/schema.d.ts`.

## Study docs export

`scripts/export-study-docs.sh` copies `docs/learning/` to the NotebookLM folder (`Mobile/` and
`Mobile - Fase N - …/`), next to the backend's folders. Add each new phase to the script.

## Gotchas

- RNTL 14: `render` (via `renderRouter`) and `fireEvent` are async — always `await` them.
- TypeScript 6 defaults `types` to `[]`: `tsconfig.json` lists `"jest"` explicitly.
- `openapi-typescript` needs TS 5 as peer: run it only via `npm run contract:sync` (pinned npx).
- Without a Redis server the backend's throttles wait for the connection timeout on every
  request: for local e2e use a settings file with an in-memory cache.
- Jest runs with `maxWorkers: 2` (package.json): with more workers the router screens time out
  on a ~3 GB machine (14/53 failed; CI was green). Same cause as the backend's Vitest cap.

## Running against the local backend

Start the Django API from the main checkout (`backend/`, see its CLAUDE.md), then
`EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npx expo start --web`. The backend must
allow the web origin in `CORS_ALLOWED_ORIGINS`. No iOS/Android emulator is available in the
agent environment: verify with tests and the web build.
