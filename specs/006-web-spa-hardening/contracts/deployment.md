# Deployment contract: the `web` service on Coolify

- Image: `infra/frontend.Dockerfile`, target `prod`; non-root (uid 101), port 8080, `expose` only.
- Build arg: `VITE_API_BASE_URL` = `${API_PUBLIC_URL}/api/v1` (baked into the bundle).
- Runtime env: `API_ORIGIN` = `${API_PUBLIC_URL}` (CSP `connect-src`).
- Routes: every path → `index.html` unless a file exists; `/assets/*` immutable cache;
  `/healthz` → 200 `ok`.
- Response headers on every page: CSP (see research §4), `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options`, `Cross-Origin-Opener-Policy`.
- Backend: `CORS_ALLOWED_ORIGINS` = the web service URL (Coolify `SERVICE_URL_WEB_8080`).
- Coolify: set the domain of `web` with suffix `:8080`, and `API_PUBLIC_URL` to the backend's
  public HTTPS URL.
