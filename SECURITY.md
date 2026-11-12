# Security policy

## Reporting a vulnerability

Please do not open a public issue. Report it privately through
[GitHub's private vulnerability reporting](https://github.com/aZaChris/MusicStudio/security/advisories/new).
You will get an answer within a week, and credit in the advisory if you want it.

Useful details: the endpoint or page, the steps to reproduce, and what an attacker gains.

## Supported versions

Only the latest release on `main` receives fixes.

## Scope

- The Django API (`backend/`), the web portal (`frontend/`) and the mobile app (branch `mobile`).
- Stripe runs in **test mode only**: no real card data is ever processed.
- Demo credentials in `seed_demo` (`password123`) are intentional: the command refuses to run
  with `DEBUG=False` unless forced with `--force`.

## How security is checked

Every development phase ends with a walk through the OWASP API Security Top 10, recorded with a
verdict and a proof for each risk in
[`docs/learning/concetti/sicurezza-api-owasp.md`](docs/learning/concetti/sicurezza-api-owasp.md).
CI runs a cross-tenant access test suite, Django's deploy checks and a secret scan (gitleaks).
