# ADR-007: Quality gate su GitHub Actions

- Stato: accettato
- Data: 2026-11-06

## Contesto

Non c'era CI. ruff c'era, ma girava solo se qualcuno si ricordava di lanciarlo. La constitution ora chiede un controllo automatico che blocca il merge.

## Decisione

Un workflow (`.github/workflows/ci.yml`) con un solo job su ogni push e pull request:

1. `uv sync --frozen` (dipendenze esattamente come nel lockfile);
2. `ruff check` e `ruff format --check`;
3. `mypy` con django-stubs e djangorestframework-stubs;
4. `makemigrations --check` (nessuna migrazione dimenticata);
5. `pytest` con copertura minima del 90%, su PostgreSQL 16 e Redis 7 come container di servizio;
6. generazione dello schema OpenAPI con `--fail-on-warn`.

In locale gli stessi controlli veloci girano con pre-commit, tramite gli hook versionati in `.githooks/`.

## Alternative scartate

- **Un job per strumento**: feedback parallelo, ma setup duplicato e più minuti per un progetto piccolo.
- **SQLite in CI**: più veloce, ma non testa i vincoli e gli indici di PostgreSQL che usiamo (indici parziali, `select_for_update`).
- **tox o nox**: un livello in più per una sola versione di Python.

## Conseguenze

- "Blocca il merge" richiede la **branch protection** su GitHub, con il check `ci / backend` obbligatorio. Non si può attivare dal codice. Va fatto da te sul branch di default, dopo aver creato `main`.
- mypy non controlla i test (vedi `docs/learning/concetti/strategia-di-test.md`).
