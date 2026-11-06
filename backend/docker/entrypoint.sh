#!/bin/sh
# Container entrypoint. The first argument selects the role; everything is env-driven.
set -eu

role="${1:-web}"

case "$role" in
  web)
    # Single web replica: migrating at start-up is the simplest safe option (ADR-003).
    # With several replicas set RUN_MIGRATIONS=0 and run `migrate` as a one-off instead.
    if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
      python manage.py migrate --noinput
    fi
    exec gunicorn config.wsgi:application \
      --bind "0.0.0.0:${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-3}" \
      --timeout "${GUNICORN_TIMEOUT:-30}" \
      --access-logfile -
    ;;
  dev)
    python manage.py migrate --noinput
    exec python manage.py runserver "0.0.0.0:${PORT:-8000}"
    ;;
  worker)
    exec celery -A config worker --loglevel "${LOG_LEVEL:-INFO}" --concurrency "${CELERY_CONCURRENCY:-2}"
    ;;
  beat)
    exec celery -A config beat --loglevel "${LOG_LEVEL:-INFO}" --schedule /tmp/celerybeat-schedule
    ;;
  *)
    exec "$@"
    ;;
esac
