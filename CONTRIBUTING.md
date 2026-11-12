# Contributing

MusicStudio is a personal portfolio and learning project, but issues and suggestions are welcome.

## Before you start

- Open an issue first for anything larger than a typo, so we can agree on the approach.
- Features follow the spec-kit flow: a spec in `specs/<NNN-name>/`, then a plan and tasks. The
  principles in [`.specify/memory/constitution.md`](.specify/memory/constitution.md) win over habit.

## Working on the code

- Branch from `main` (API and web portal) or `mobile` (Expo app) and open a pull request back to it.
- One Django app per domain: writes in `services.py`, reads in `selectors.py`, thin views and
  serializers. Tenant scoping only through `apps/common/scoping.py`.
- Every change ships its tests, including cross-tenant read and write tests for new endpoints.
- After changing serializers or views, regenerate `backend/openapi.yaml` and the frontend types.
- Run the quality gate from the [README](README.md#quality-gate-the-same-as-ci); CI runs the same.
- Code, comments and commit messages in English. Commit bodies explain **why**.

## Reporting bugs

Use the issue templates. For security problems follow [SECURITY.md](SECURITY.md) instead.
