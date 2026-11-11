# Quickstart: validate phase 007

Prerequisites: PostgreSQL 16 reachable through `DATABASE_URL` (on a peer-auth machine
`postgres://$USER@/musicstudio`), `cd backend && uv sync`, `cd frontend && npm ci`.
Emails print to the backend console in dev. No Stripe keys are needed and no payment is made.

## 1. Quality gate

```bash
cd backend
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test --noinput
rtk proxy uv run pytest            # coverage >= 90%, all green
uv run python manage.py spectacular --settings=config.settings.test --fail-on-warn --file openapi.yaml
cd ../frontend && npm run typecheck && npm run lint && npm test && npm run build
```

## 2. Manual walk (dev server + portal)

```bash
cd backend && uv run python manage.py runserver      # terminal 1
cd frontend && npm run dev                           # terminal 2, http://localhost:5173
```

1. **Registration (US1)**: open `/register`, create an owner. The confirmation link appears in
   terminal 1. Before confirming, sign-in is refused; after, the empty dashboard appears.
   Registering again with the same email shows the same message; terminal 1 shows the
   "someone tried to register" email instead of a new confirmation.
2. **Reset (US2)**: `/forgot-password` with a real and a fake address: same screen. Use the
   link, set a new password; a second browser that was signed in is logged out on its next
   refresh.
3. **Invitations (US3)**: as owner invite a teacher; as teacher create a student and invite a
   parent; accept both from the console links; the parent's consent appears on their data page.
4. **Lockout (US5)**: 5 wrong passwords, then the right one is refused; `manage.py
   unlock_account <email>` lifts it and appears in the audit view.
5. **MFA (US5)**: enable from the account page with an authenticator app (manual key), sign out,
   sign in with the code, then with a recovery code; the same recovery code fails the second time.
6. **Privacy (US6)**: as parent download the export and check it lists only your children;
   request erasure; sign-in fails; as owner the student shows as "Allievo cancellato" and
   payment totals are unchanged.
7. **Adult student (US7)**: mark a student adult, invite, accept, see read-only data; a minor
   cannot be invited as student.
8. **Audit (US8)**: as owner open `/audit`: every action above is listed; as teacher the page is
   not available.

## 3. Security checks

- Encrypted notes: `psql -d musicstudio -c "select notes from lessons_lesson where notes <> '' limit 1"`
  shows a Fernet token (`gAAAA...`), not text.
- Secret scan: CI job `secrets` green on the branch; a test commit with a fake key on a
  throwaway branch makes it red (do not push real keys).
- IDOR suite: `rtk proxy uv run pytest -m idor -v` lists every endpoint × role pair.
