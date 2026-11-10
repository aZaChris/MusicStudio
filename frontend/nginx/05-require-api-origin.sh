#!/bin/sh
# Fail fast: without API_ORIGIN the CSP would contain a literal "${API_ORIGIN}" and the SPA
# could not reach the API. Better a container that refuses to start than a silently broken one.
set -eu
case "${API_ORIGIN:-}" in
  https://*|http://localhost*|http://127.0.0.1*) ;;
  *) echo "API_ORIGIN must be the API's origin, e.g. https://api.example.com (got '${API_ORIGIN:-}')" >&2; exit 1 ;;
esac
