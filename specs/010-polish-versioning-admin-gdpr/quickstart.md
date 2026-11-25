# Quickstart: validating the Polish phase

Prerequisites: PostgreSQL running, `DATABASE_URL` set as in the project README,
`cd backend && uv sync`. Nothing here builds the mobile app or deploys.

## 1. Quality gate

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test --noinput
rtk proxy uv run pytest
uv run python manage.py spectacular --settings=config.settings.test --fail-on-warn --file openapi.yaml
git diff --stat openapi.yaml     # expected: empty, or only deprecation flags
```

## 2. Versioning (US1, FR-001..004)

- `uv run pytest apps/common/tests/test_deprecation.py`: headers present, contract flag, `410`
  after the sunset date, notice shorter than 90 days rejected.
- Contract diff: `oasdiff breaking <contract-on-main> backend/openapi.yaml` prints no error.
  Then rename a response field on a scratch copy and confirm it fails (record the output in
  `research.md` R2).

## 3. Admin (US2, FR-005..010)

- `uv run pytest apps/common/tests/test_admin_gate.py apps/common/tests/test_admin_inventory.py`
  covers every role, TOTP on/off, lockout, IP allowlist, read-only models, audit entries,
  hidden fields.
- Manual, optional: run the dev server, sign in at the admin as an operator, open a payment and
  see no Save or Delete buttons; open an audit entry and a user.

## 4. Export (US3, FR-011..015)

- `uv run pytest apps/privacy/tests/test_export_inventory.py apps/privacy/tests/test_export_completeness.py`.
- Timing: the seeded family test prints the export time; record it in `research.md` R8
  (must be under 10 s on this machine, otherwise implement the background export).

## 5. Portfolio (US4, FR-016..018)

- Run each command the README shows, from a clean clone in a scratch directory, and compare.
- Hand the README to someone who does not know the project and ask the five questions of the
  independent test of US4.
- Copy the study docs for NotebookLM at the end of the phase
  (`scripts/export-study-docs.sh`, destination as in `CLAUDE.md`).
