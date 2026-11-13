# syntax=docker/dockerfile:1
# React SPA image (ADR-025).
#   dev:   Vite dev server, used by docker-compose.yml (--profile frontend)
#   prod:  static build served by a non-root nginx on port 8080, used on Coolify
# Base images are pinned: an unpinned tag changes under you between two builds.

FROM node:22.12.0-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS build
# The API address is baked into the bundle at build time (Vite replaces import.meta.env).
ARG VITE_API_BASE_URL
RUN test -n "$VITE_API_BASE_URL" || { echo "VITE_API_BASE_URL build arg is required" >&2; exit 1; }
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
# Optional: where to download the Android app (shown on the landing and after sign-in).
ARG VITE_ANDROID_APK_URL=
ENV VITE_ANDROID_APK_URL=$VITE_ANDROID_APK_URL
# Public address of the site, for the canonical link and the share preview (vite.config.ts).
ARG VITE_SITE_URL=
ENV VITE_SITE_URL=$VITE_SITE_URL
COPY . .
RUN npm run build

# nginx-unprivileged: runs as uid 101, listens on 8080, renders /etc/nginx/templates/*.template
# with the container's environment at start (API_ORIGIN for the CSP).
FROM nginxinc/nginx-unprivileged:1.27.3-alpine AS prod
COPY --chmod=755 nginx/05-require-api-origin.sh /docker-entrypoint.d/05-require-api-origin.sh
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
# Safe by default: a site nobody opened to search engines stays out of them. Production sets
# ROBOTS_TAG="index, follow" on purpose.
ENV ROBOTS_TAG="noindex, nofollow"
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
