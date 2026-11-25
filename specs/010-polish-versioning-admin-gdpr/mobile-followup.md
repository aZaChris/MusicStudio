# Follow-up for the `mobile` branch (phase 10)

Nothing in the mobile app breaks with this phase: no endpoint was removed or renamed, and the
contract only gained three values in the audit action list (`admin.login`, `admin.change`,
`admin.delete`). What the mobile developer should do, in order of importance:

1. **Handle unknown enum values everywhere.** The contract-diff job treats a new value in a
   response enum as compatible (policy: `docs/operations/api-versioning-policy.md`). Any
   `switch` on `status`, `action`, `method` or similar needs a default branch that shows the raw
   value or ignores it, never crashes.
2. **Send `X-Client: mobile/<app version>`** on every request. Calls to deprecated endpoints are
   logged with this value only, so we can see which app versions still use them before removal.
3. **Read the deprecation headers** in the API client: when a response carries `Deprecation`,
   log it in development builds (and optionally report it to Sentry) with the `Sunset` date and
   the `successor-version` link. No endpoint is deprecated today; this is for the first one.
4. **Treat `410` with code `endpoint_gone`** as "update the app": show a message asking the user
   to update, not a generic error.
5. **GDPR export** (`GET /api/v1/privacy/export/`) gained new top-level keys (`reminders`,
   `online_checkouts`, `invitations`, `activity`) and new fields (`account.mfa_enabled`,
   `children[].anonymised_at`, `payments[].reversal_of`, `payments[].receipt_number`). The app
   only downloads the file, so nothing to change unless it parses it.

The admin changes (operators only, TOTP) do not affect the app: studio accounts never used the
admin.
