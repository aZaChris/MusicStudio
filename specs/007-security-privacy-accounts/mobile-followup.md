# Mobile follow-up (phase 007)

The app lives on `staging/mobile` and is **not** changed by phase 7. This lists what it needs
to use the new backend. All paths are under `/api/v1/`; the machine-readable contract is
`backend/openapi.yaml`.

## Sign-in changes (breaking for the current login screen)

- `POST auth/token/` can now answer `200 {mfa_required: true, mfa_token}` instead of the token
  pair. Only owners and teachers who enabled MFA get it; parents and students never do.
  The app must show a code field and call `POST auth/mfa/verify/ {mfa_token, code}`; the
  code can be the 6-digit TOTP or a recovery code. `mfa_token` lives 5 minutes.
- Failed sign-in answers 401 with one generic body whether the password is wrong, the
  address is unknown or the account is locked after 5 failures. Show one message
  ("email o password errati, o account temporaneamente bloccato"); never say which.
- `401` with `code: email_not_confirmed` (only after a correct password): offer
  `POST auth/confirm-email/resend/ {email}`.
- `GET auth/me/` adds `email_verified`, `mfa_enabled` and the role `student`.

## Screens by role

Parent (the main app user):
- Accept an invitation: deep link `…/invitations/accept?token=` →
  `GET invitations/lookup/?token=` → form (password, first name, consent checkbox with the
  notice) → `POST invitations/accept/` (returns the token pair).
- Forgot password: `POST auth/password-reset/ {email}` (always 202), the link opens the
  portal (`/reset-password?uid=&token=`); the app only needs to send the person there or
  handle the same deep link with `POST auth/password-reset/confirm/`.
- Change password: `POST auth/password/change/` — every session ends, sign in again.
- Privacy screen: `GET privacy/consents/`, `POST privacy/consents/{id}/withdraw/ {password}`,
  `GET privacy/export/` (JSON attachment: save/share it), `POST privacy/erase/ {password}`
  (409 `checkout_open` while an online payment is pending; confirm with a clear warning:
  it cannot be undone).

Adult student (new role, read-only): the same lists as a parent for their own record only
(`students/`, `lessons/`, `packages/`, `payments/`), and the same privacy screen. Every write
answers 403, so hide the action buttons.

Teacher / owner (only if the app gets a teacher mode): MFA setup (`auth/mfa/setup/`,
`auth/mfa/confirm/` → 10 recovery codes shown once, `auth/mfa/disable/`,
`auth/mfa/recovery-codes/`), invitations (`invitations/`, `…/revoke/`), audit list for owners
(`audit/`).

## Not for the app

Registration of a new studio (`auth/register/`) stays on the portal.
