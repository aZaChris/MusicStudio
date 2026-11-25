# API versioning and deprecation policy

This page is for developers of clients of the MusicStudio API: the web portal, the mobile app
and any other integration. It says what the API promises, how a change that breaks clients is
announced, and how long the old behaviour keeps working.

Decision record: `docs/learning/adr/ADR-040-versionamento-e-deprecazione-api.md` (Italian).

## What `v1` promises

Everything under `/api/v1/` follows the published contract, `backend/openapi.yaml` on the
`main` branch. Within `v1` we only make **compatible** changes:

- new endpoints;
- new optional request fields;
- new fields in responses;
- new values in a list of values that is meant to grow (for example audit actions or
  payment statuses). **Clients must handle values they do not know**, for example by showing
  them as they are or by ignoring them.

## What counts as breaking

Any change that can make a correct client fail:

- removing or renaming an endpoint, a response field or a request field;
- changing the type or the format of a field;
- making an optional request field required, or adding a new required request field;
- narrowing the values a request field accepts;
- changing the meaning of a status code or of an error `code`.

A breaking change is never made silently. Every pull request runs `oasdiff breaking` against
the contract on `main` and fails on a breaking change. The only way through is a line in
`.github/oasdiff-ignore.txt` with the reason and the link to the pull request, so the
decision is visible and reviewed.

## Minimum notice: 90 days

An endpoint is removed at least **90 days** after it is announced as deprecated. Mobile apps
update slowly through the stores, so a shorter notice would break installed apps. The code
refuses a shorter notice at start-up.

## Where a deprecation is announced

You will find it in four places, so it cannot go unnoticed:

1. **In every response** of the deprecated endpoint:

   ```text
   Deprecation: @1796083200
   Sunset: Wed, 31 Mar 2027 00:00:00 GMT
   Link: </api/v2/things/>; rel="successor-version", <this page>; rel="deprecation"
   ```

   `Deprecation` is the date it was deprecated (RFC 9745, seconds since 1970). `Sunset` is the
   removal date (RFC 8594). The `successor-version` link is present only when there is a
   replacement.
2. **In the contract**: the operation is marked `deprecated: true` and its description starts
   with the removal date. Generated clients show it as deprecated.
3. **In the register**: [`docs/operations/deprecations.md`](deprecations.md), one row per
   deprecation, with the removal date and the replacement.
4. **In a migration report** in [`docs/operations/migrations/`](migrations/): what changes, old
   and new request and response side by side, the steps for each client, a test checklist and
   the rollback.

Please send the header `X-Client: <app>/<version>` (for example `X-Client: mobile/1.4.2`).
Calls to deprecated endpoints are logged with that value only, so we can see who still uses
them before the removal date. No personal data is logged.

## After the removal date

The endpoint answers `410 Gone` with the usual error body:

```json
{"code": "endpoint_gone", "detail": "This endpoint was removed on 2027-03-31. See <this page>."}
```

It never starts answering differently without notice, and never answers a generic `404`.

## How a new version is introduced

A `v2` is created only when a real breaking change is needed. The new version lives next to
the old one (`/api/v2/...` beside `/api/v1/...`). The `v1` endpoints it replaces are deprecated
with at least 90 days of notice, their `Link` header points to the `v2` replacement, and the
migration report explains the move. When the replacement is a different service rather than a
new version, the migration report covers how to authenticate to it and how the data maps.
