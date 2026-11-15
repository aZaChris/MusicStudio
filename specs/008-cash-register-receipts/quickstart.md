# Quickstart: validate phase 008

Prerequisites: PostgreSQL 16 reachable through `DATABASE_URL` (on a peer-auth machine
`postgres://$USER@/musicstudio`), `cd backend && uv sync`, `cd frontend && npm ci`.
No Stripe keys are needed: card entries are created by tests only. Contracts:
[contracts/api.md](contracts/api.md); tables: [data-model.md](data-model.md).

## 1. Quality gate

```bash
cd backend
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test --noinput
rtk proxy uv run pytest            # coverage >= 90%, all green
uv run python manage.py spectacular --settings=config.settings.test --fail-on-warn --file openapi.yaml
cd ../frontend && npm run typecheck && npm run lint && npm test && npm run build
```

The generated types in `frontend/src/api/schema.d.ts` must match `backend/openapi.yaml`.

## 2. Manual walk (dev server + portal)

```bash
cd backend && uv run python manage.py runserver      # terminal 1
cd frontend && npm run dev                           # terminal 2, http://localhost:5173
```

Sign in as a studio owner with a few students and packages (use `manage.py create_teacher` and
the portal, or `seed_loadtest` for volume).

1. **Correct a mistake (US1)**: record a cash payment of 40 for student A and mark it paid. Open
   the register, reverse it with a reason. Check: the original is still listed and marked
   reversed; a reversal row shows who, when and why; the month's net is zero; student A's package
   is payable again. Try to edit or delete the paid entry through the API: 409 `payment_final`.
   Delete a pending entry: it works, and the audit view shows `payment.delete`.
2. **Totals and export (US2)**: record entries by cash, bank transfer, manual and (in a test) card
   on different days. Open a month: received, reversed and net, overall and per method, match a
   hand calculation. Export CSV and open it in a spreadsheet: accents are right, one row per entry,
   a student named `=SUM(A1)` shows as text. Export PDF: studio name, period, totals per method,
   production date. A period longer than a year is refused with a clear message.
3. **Tell parents how to pay (US3)**: as owner open the payment instructions page, enter holder,
   a valid IBAN and one `https` link; an invalid IBAN or an `http` link is refused. As a linked
   parent, open the portal: the instructions appear beside an open package, with the statement that
   payment happens outside MusicStudio. A package that is paid, or a studio with no instructions,
   shows nothing. A parent of another studio sees nothing of it. A teacher of the studio can read
   but not save.
4. **Receipt (US4)**: as teacher issue the receipt of a paid entry; download the PDF: studio,
   student, amount, date, method, number `YYYY-NNNN`, the "not a tax document" sentence. Issue it
   again: same number. Reverse the entry: the receipt now carries the cancelled mark. As the
   parent of that student, download it from the portal; another parent gets 404.
5. **Privacy**: as the owner, export your data (it includes the instructions); as a parent, request
   erasure of the family, then open the register as owner: amounts, dates and receipt numbers are
   there, the name is the anonymised label.

## 3. Automated proofs to look for

- Concurrency: two reversals of one entry at once give one 201 and one 409; twenty receipts at
  once in one studio give twenty distinct, gapless numbers.
- Leaks: every new endpoint has a cross-studio read and write test returning 404 (FR-032, SC-006).
- Logs: a failing `PUT payment-instructions/` with an IBAN leaves no IBAN in the logs, the audit
  log or the captured Sentry event (SC-008).
- Query budgets: the register list, the summary, the open-instructions list and the receipt list
  hold a constant number of queries when the data grows.
- Volume: a studio with 2,000 entries in a month answers the summary and list in under 3 s; a
  year of 5,000 entries exports in under 10 s (seed with `seed_loadtest`, then time the calls).
