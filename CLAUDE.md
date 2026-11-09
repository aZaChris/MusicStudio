# MusicStudio — working rules for Claude Code

Read this first in every session. It travels with the repository, so it applies on any
machine. Answer the user (Christian) **in Italian**: he is a developer with ~1.5 years of
experience, English B1, and studies everything that is built here.

## What this project is

- A Django REST API for music teachers and small studios (lessons, packages, payments,
  parent portal). Two goals: a production-grade backend portfolio, and training the owner to
  mid-level backend skills. **The study documentation is a deliverable as much as the code.**
- Work happens on branch `refactor/production-standards` (based on the Django commit
  `4be062d`, see `docs/learning/adr/ADR-001-*`). Branches `web` (Next.js) and `app` (Expo)
  are earlier rewrites: never modify them. There is no `main` yet.
- Principles: `.specify/memory/constitution.md` (v2.0.0). They override habits; re-read the
  relevant principle before deciding.

## Roadmap and status

| Phase | Feature dir | Status |
|---|---|---|
| 1 Foundations | `specs/002-production-foundations` | done |
| 2 Domain | `specs/003-domain-integrity` | done |
| 3 Celery & payments | `specs/004-celery-payments` | done |
| 4 Production (Coolify deploy, Sentry, JSON logs, Locust, off-site backups + restore drill, full OWASP, token revocation, Stripe IP allowlist) | `specs/005-production-readiness` | done (owner tasks open: real Coolify deploy T018, bucket drill T024) |
| 5 Polish (API versioning/deprecation, admin hardening, GDPR export, portfolio write-up) | — | later |

Open items carried over are listed at the end of `docs/learning/00-indice.md`.

## How to work

- **Spec-kit flow** per phase: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`. `.specify/feature.json` points to the active feature.
- **Autonomy**: work autonomously until the phase is complete, then stop with a summary in
  Italian (what changed, what is open, which docs to read). If an ambiguous choice changes the
  architecture significantly, pick the simplest conservative option, record an ADR, continue.
- **Commits**: small, in English, body explains *why* (it becomes the diary in the owner's
  vault). Commit on the working branch; push only when the user asks.
- **Code**: modular monolith, one app per domain; writes in `services.py`, reads in
  `selectors.py`, thin views/serializers. Tenant scoping only through
  `apps/common/scoping.py` + `TenantContext`. Every feature ships tests (cross-tenant
  read/write tests, query budgets on main endpoints). No AWS. `frontend/` is out of scope:
  never modify it. Stripe: **test mode only**, all calls in `apps/payments/gateway.py`.
- **Code, comments, identifiers, commits: English. Study docs: Italian.**

## Local setup and quality gate

```bash
cd backend && uv sync
git config core.hooksPath .githooks        # once per clone: pre-commit via versioned hooks
export DATABASE_URL=postgres://USER@localhost:5432/musicstudio   # PostgreSQL 16 required
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test --noinput
uv run pytest                               # coverage floor 90%
uv run python manage.py spectacular --settings=config.settings.test --fail-on-warn --file openapi.yaml
```

CI (`.github/workflows/ci.yml`) runs the same; `backend/openapi.yaml` must be regenerated
whenever serializers/views change.

## Study documentation (`docs/learning/`, Italian)

- `00-indice.md` (map + reading order), `audit-iniziale.md`, `01-panoramica-architettura.md`,
  `adr/ADR-NNN-titolo.md` (contesto, decisione, alternative scartate, conseguenze; next number
  after the highest existing one), `concetti/<argomento>.md`, `glossario.md`,
  `colloquio/domande-e-risposte.md`.
- **Concept doc format** (800–1500 words, check with `wc -w`): TL;DR (3–4 lines); il problema
  reale; come funziona con un'analogia; come lo abbiamo applicato in MusicStudio (file paths,
  code ≤ 15 lines, before/after); alternative considerate; errori comuni e trade-off; come lo
  spiegheresti a un colloquio (5 frasi); 5 domande di autoverifica con risposta.
- Style: every file understandable on its own (loaded alone into NotebookLM), short sentences,
  spoken tone (some become audio), clean Markdown, no complex tables. Never invent: use real
  measurements and outputs; if a choice is debatable, say so.
- When a phase changes something an older doc describes as current, update that doc too
  (the audit stays historical).
- Non-trivial problems solved → `docs/knowledge-base/<slug>.md` (Sintomo, Causa radice, Come
  l'abbiamo confermata, Risoluzione, Lezione per il futuro, Riferimenti) + a row in its README.

## End of a phase (checklist)

1. All tasks of the feature marked `[X]`; full quality gate green.
2. OWASP API Top 10 walk updated in `docs/learning/concetti/sicurezza-api-owasp.md`.
3. Glossary, interview Q&A, overview and `00-indice.md` (reading order + "Riepilogo della
   fase N") updated.
4. Phase summary commit ("Complete phase N: ...").
5. **Copy the study docs for NotebookLM**: add the phase to the `PHASES` list in
   `scripts/export-study-docs.sh` (folder `Fase N - <Nome>`, its concept files, its ADR
   range), then run it. Destination: `$STUDY_DOCS_DIR`, defaulting to
   `/mnt/c/Users/Christian/Documents/doc_music_studio`. If neither exists on this machine,
   ask the user where to copy. Tell the user which files are NEW/UPDATED.
6. If the Obsidian vault sync exists on this machine (`~/.config/git/obsidian_sync.py`),
   append the phase's decisions to `20 Progetti/MusicStudio/Decisioni MusicStudio.md` in the
   vault (table: Scelta | Perché | Scartato).

## Gotchas learned the hard way

- `makemigrations` prompts interactively on NULL → NOT NULL changes and hangs: use
  `--noinput`, and split data migrations from schema changes (PostgreSQL refuses ALTER TABLE
  with pending deferred FK checks in the same transaction).
- Durations: compute in UTC (`end_of()` in `apps/lessons/services.py`); wall-clock arithmetic
  on Europe/Rome datetimes is wrong on DST nights.
- Lesson overlap: concurrent inserts can deadlock on the exclusion constraint; writes go
  through `_guarded_write` (retry, then 409).
- Query budgets: authenticate tests with a fresh user (`client_for`) and clear the cache
  before measuring.
- Redis down must not take the API down: throttles fail open (`apps/common/throttling.py`).
- Never `pkill -f <pattern>` in a shell whose own command line contains the pattern.
- rtk's pytest filter can hide errors (it showed "22 passed" with 1 error): run pytest
  through `rtk proxy` when the exact result matters.
- Seed load-test data with the SAME settings as the server: test settings hash passwords
  with MD5, which production settings reject (every login 401).
- Never print or read credential files (`.env.local`, `.pgpass`); `.env.local` on the main
  machine holds real Neon credentials from the `app` branch and is git-ignored.
