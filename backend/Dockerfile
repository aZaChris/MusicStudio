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
# variables (config/tests/test_dockerfile_build_env.py keeps this list complete).
# These throwaway values exist only for this build step; the Fernet key is a fake one
# (production refuses the public development key on purpose), never a real key.
# `env -i` starts from an empty environment: Coolify injects every app variable as a build
# ARG, empty ones included, and TRUSTED_PROXY_COUNT='' crashed env.int() here.
RUN env -i PATH=/usr/local/bin:/usr/bin:/bin \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_SECRET_KEY=build-only JWT_SIGNING_KEY=build-only \
    DATABASE_URL=postgres://build@localhost/build \
    DJANGO_ALLOWED_HOSTS=build DJANGO_CSRF_TRUSTED_ORIGINS=https://build \
    SMTP_HOST=build SMTP_USER=build SMTP_PASSWORD=build \
    FRONTEND_URL=https://build \
    FIELD_ENCRYPTION_KEYS=YnVpbGQtb25seS10aHJvd2F3YXkta2V5LTAwMDAwMDA= \
    /opt/venv/bin/python manage.py collectstatic --noinput

# ---- runtime: small, non-root ------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8000

# No RUN in this stage: Coolify injects every variable (secrets included) as a build ARG,
# and a RUN would record them in the image history. A numeric uid needs no useradd.
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=10001:10001 /app /app

USER 10001:10001
EXPOSE 8000

# Liveness only: a database outage must not make Docker kill healthy web containers.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "docker/healthcheck.py", "http", "/health/live/"]

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["web"]
