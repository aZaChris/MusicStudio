# syntax=docker/dockerfile:1
# MusicStudio backend image: one image, three roles (web, worker, beat) chosen by CMD.

# ---- builder: resolve dependencies and collect static files ----------------------------
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /bin/uv
# The venv lives outside /app so a dev bind-mount of the source never hides it.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
# Dependencies first: this layer is cached until pyproject.toml/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

COPY . .
# collectstatic imports production settings, which refuse to load without their
# variables. These throwaway values exist only for this build step.
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_SECRET_KEY=build-only JWT_SIGNING_KEY=build-only \
    DATABASE_URL=postgres://build@localhost/build \
    DJANGO_ALLOWED_HOSTS=build DJANGO_CSRF_TRUSTED_ORIGINS=https://build \
    SMTP_HOST=build SMTP_USER=build SMTP_PASSWORD=build \
    /opt/venv/bin/python manage.py collectstatic --noinput

# ---- runtime: small, non-root ------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8000

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=app:app /app /app

USER app
EXPOSE 8000

# Liveness only: a database outage must not make Docker kill healthy web containers.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "docker/healthcheck.py", "http", "/health/live/"]

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["web"]
