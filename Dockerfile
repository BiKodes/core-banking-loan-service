FROM python:3.12.9-bullseye

SHELL ["/bin/sh", "-c"]

COPY . /opt/core-banking-loan-service/
WORKDIR /opt/core-banking-loan-service/

ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONFAULTHANDLER 1 \
    PYTHONUNBUFFERED 1 \
    PATH=/usr/local/nginx/bin:$PATH \
    DJANGO_ENV=production \
    DJANGO_SETTINGS_MODULE=config.production \
    DJANGO_CONFIGURATION=Production

RUN pip install --quiet --no-cache-dir pip==23.2.1 \
    apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY ./LICENSE LICENSE
COPY ./requirements/ /opt/core-banking-loan-service/requirements/
RUN pip install --no-cache-dir -r requirements/$REQUIREMENTS.txt

EXPOSE 8000

VOLUME ["/opt/core-banking-loan-service"]

RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt bullseye-pgdg main" > /etc/apt/sources.list.d/postgres.list' \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt update && apt -y install postgresql-client-16 && rm -rf /var/lib/apt/lists/*

COPY . .

COPY ./entrypoint.sh /opt/core-banking-loan-service/
RUN chmod 755 /opt/core-banking-loan-service/entrypoint.sh
ENTRYPOINT ["sh", "/opt/core-banking-loan-service/entrypoint.sh" ]

# Run gunicorn as the default command; default to 8000 when PORT is unset
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} config.wsgi:application"]
