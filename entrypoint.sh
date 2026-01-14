#!/bin/sh
set -e

python manage.py migrate --no-input
python manage.py collectstatic --no-input

DJANGO_SUPERUSER_PASSWORD=$SUPER_USER_PASSWORD python3 manage.py createsuperuser --username $SUPER_USER_NAME --email $SUPER_USER_EMAIL --noinput

PORT=${PORT:-8000}

gunicorn --bind :$PORT \
    src.config.wsgi:application --access-logfile - --error-logfile - --log-level info

echo "Done setting core-banking-loan-service configurations"
exec "$@"
