# Data Model: Polish phase

No new tables. One migration: the `choices` of `AuditEntry.action` grow (Django records choices
in migrations, as in phases 8 and 9).

## Changed

- **AuditEntry.action** gets three values:
  - `admin.login`: an operator signed in to the admin (outcome success, failure or denied).
  - `admin.change`: an object was created or changed from the admin. Metadata: model label,
    object id, names of the changed fields (never values).
  - `admin.delete`: an object (or a set of objects) was deleted from the admin. Metadata:
    model label, ids or count. Expected to be rare, since final records cannot be deleted.

## Code-level structures (no database)

- **Deprecation notice**: arguments of the decorator: `since` (date), `sunset` (date),
  `successor` (path or none). Rule: `sunset` is at least `since` plus the policy notice
  (90 days); a test fails on shorter notices.
- **Operator**: a `User` with `is_staff` and `is_active` and no studio role (field `role` empty
  or not used). Rule: studio roles never get `is_staff`. A test creates each role and checks the
  gate.
- **Export inventory**: `dict[str, tuple[Literal["exported","excluded"], str]]`, key
  `app_label.ModelName`. Rule: every model of the project apps has an entry; for `exported` the
  string is a key that must appear in `build_export`; for `excluded` it is a reason of at
  least ten characters.

## Settings

- `ADMIN_REQUIRE_TOTP` (bool, default false; true in `prod`).
- `ADMIN_ALLOWED_IPS` (comma list, default empty; documented in `.env.example`).
- `API_DEPRECATION_MIN_NOTICE_DAYS` (int, default 90), used by the test and the policy.
