# Deprecation register

One row per deprecated endpoint. The source of truth is the code (`@deprecated` in
`backend/apps/common/deprecation.py`): the test
`backend/apps/common/tests/test_deprecation_register.py` fails when a deprecation in the code has
no row here with the same endpoint and removal date, or when its migration report is missing.
A weekly workflow (`.github/workflows/deprecation-watch.yml`) turns red 30 days before each
removal date.

Policy: [api-versioning-policy.md](api-versioning-policy.md). New report: copy
[migrations/TEMPLATE.md](migrations/TEMPLATE.md).

| Endpoint | Announced | Removal date | Replacement | Migration report | Status |
| --- | --- | --- | --- | --- | --- |

No active deprecations (2026-11-25).
