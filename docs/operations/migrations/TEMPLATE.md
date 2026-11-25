# Migration report: <endpoint> (TEMPLATE)

Copy this file to `docs/operations/migrations/<short-name>.md`, fill every section, add the row
to [`../deprecations.md`](../deprecations.md), then add `@deprecated(..., report=...)` to the
view. A deprecation without this report is refused by the tests.

## 1. What changes and why

- Endpoint: `<METHOD /api/v1/...>`
- Replacement: `<METHOD /api/v2/...>`, or another service (see section 6), or none
- Why: <the real reason, in two or three sentences>

## 2. Who is affected

- Web portal (`frontend/`): <yes/no, which pages>
- Mobile app (`mobile` branch): <yes/no, which screens; write the follow-up note for the branch>
- Other clients: <known integrations, or "none known">
- Calls in the last 30 days: <from `deprecation_report`, or "unknown">

## 3. Old and new, side by side

Old request and response:

```http
<old request>
```

```json
<old response>
```

New request and response:

```http
<new request>
```

```json
<new response>
```

Field mapping: `<old field>` becomes `<new field>` (<conversion, if any>).

## 4. Steps for each client

- Web portal: <regenerate types from `backend/openapi.yaml`, change these calls, ...>
- Mobile app: <...>
- Other clients: <...>

## 5. Test checklist

- [ ] The new call returns the same data as the old one for a real account
- [ ] Unknown values and new fields are handled
- [ ] The client no longer calls the old endpoint (check the `deprecated_call` log lines)
- [ ] The client sends `X-Client: <app>/<version>`

## 6. Moving to a different service (only if the replacement is not a new API version)

- What the new service is and who runs it: <...>
- How to authenticate: <...>
- Data mapping and data that is not carried over: <...>
- Cut-over: <how and when clients switch, and how long both work in parallel>

## 7. Timeline

- Announced (deprecation date, `Deprecation` header): <YYYY-MM-DD>
- Warning (30 days before removal, the weekly check turns red): <YYYY-MM-DD>
- Removal (`Sunset` header, then `410 Gone`): <YYYY-MM-DD>, at least 90 days after the announcement

## 8. Rollback

<How to bring the old endpoint back if the removal breaks a client we did not know about:
revert the removal commit, extend the date in the register with a written reason, tell the
client developers.>
