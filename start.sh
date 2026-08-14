#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py seed_menu

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
