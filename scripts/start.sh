#!/bin/sh

set -e
set -x

python manage.py migrate --no-input
python manage.py collectstatic --no-input

PORT=${PORT:-8000}
gunicorn src.config.wsgi:application -b 0.0.0.0:${PORT}
