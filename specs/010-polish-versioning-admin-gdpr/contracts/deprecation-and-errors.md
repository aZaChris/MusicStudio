# Contract changes: deprecation signals and the "gone" error

No endpoint is added or removed in this phase. A real endpoint is deprecated only when a
breaking change is actually needed; the mechanism is proved on a test-only view.

## Response headers of a deprecated endpoint

```text
Deprecation: @1796083200          (RFC 9745: the deprecation date, Unix seconds)
Sunset: Wed, 31 Mar 2027 00:00:00 GMT
Link: </api/v2/lessons/>; rel="successor-version", <policy URL>; rel="deprecation"
      (successor-version only when a successor exists)
```

The body and status code are exactly those of the endpoint before the deprecation.

## OpenAPI

The operation carries `deprecated: true` and its description starts with the removal date.
Generated clients (the portal's types, the mobile contract check) show it as deprecated.
Nothing else in `openapi.yaml` changes in this phase, so the contract diff must be empty.

## After the sunset date

```text
HTTP/1.1 410 Gone
{"code": "endpoint_gone", "detail": "This endpoint was removed on 2027-03-31. See <policy link>."}
```

The shape follows the project's error envelope (`apps/common/exceptions.py`); implementation
must reuse it and check the exact keys there before writing the test.

## Admin responses

- Not an operator, or IP not allowed: `404` (the admin does not confirm it exists).
- Operator without a valid code in production: the login form shows a generic error; no
  message tells which part was wrong; the failure counts toward the lockout.
- Locked account: the same message and timing rules as the API sign-in.

## Export

Same endpoint and method (`GET /api/v1/privacy/export/`), same attachment name. New keys may be
added to the JSON (adding keys is not breaking); no existing key is renamed or removed.
