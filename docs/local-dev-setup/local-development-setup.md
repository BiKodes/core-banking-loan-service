# Local Development Setup

## Prerequisites

```bash
sudo apt update
sudo apt install python3.10 python3.10-venv postgresql postgresql-contrib
```

## 1. Clone and Setup Virtual Environment

- ```bash 
git clone git@github.com:BiKodes/core-banking-loan-service.git
```

```bash
cd ~/dev/dmi/core-banking-loan-service
python3 -m venv venv
source venv/bin/activate

# Or if using virtualenvwrapper run this command
workon core-banking
```

## 2. Install Dependencies

```bash
pip install -r requirements/dev.txt
pip install django-environ django-cors-headers djangorestframework-simplejwt drf-yasg psycopg2-binary gunicorn
```

## 3. Configure Environment Variables

Create `.env/test.sh`

```bash
export DJANGO_SETTINGS_MODULE=src.config.local
export DJANGO_CONFIGURATION=LOCAL
export DJANGO_DEBUG=True
export DJANGO_SECRET_KEY="your-secret-key-here"
export POSTGRES_NAME="loans"
export POSTGRES_USER="loans"
export POSTGRES_PASSWORD="loans"
export POSTGRES_PORT="5433"
```

Generate a secret key

```bash
python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Load environment variables

```bash
source .env/test.sh
```

## 4. Setup PostgreSQL Database

Check PostgreSQL port

```bash
sudo -u postgres psql -c "SHOW port;"
```

Create database and user

```bash
sudo -u postgres createdb loans
sudo -u postgres psql -c "CREATE USER loans WITH PASSWORD 'loans';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE loans TO loans;"
sudo -u postgres psql -c "ALTER USER loans CREATEDB;"
```

## 5. Run Database Migrations

```bash
source .env/test.sh && python manage.py migrate
```

## 6. Create Superuser (Optional)

```bash
source .env/test.sh && python manage.py createsuperuser
```

## 7. Run Development Server

```bash
source .env/test.sh && python manage.py runserver
```

Server will be available at: **http://127.0.0.1:8000/**

Admin panel: **http://127.0.0.1:8000/admin/**

## 8. Run System Check

```bash
source .env/test.sh && python manage.py check
```

## Alternative: Using SQLite (No PostgreSQL Required)

For quick local testing without PostgreSQL add Sqlite to envs files

```bash
export USE_SQLITE=True

source .env/test.sh && python manage.py migrate
source .env/test.sh && python manage.py runserver
```

## Common Commands

### Run tests
```bash
source .env/test.sh && python manage.py test
```

### Create a new Django app
```bash
source .env/test.sh && python manage.py startapp app_name
```

### Make migrations
```bash
source .env/test.sh && python manage.py makemigrations
```

### Collect static files
```bash
source .env/test.sh && python manage.py collectstatic
```

### Run Django shell
```bash
source .env/test.sh && python manage.py shell
```

## Troubleshooting

### PostgreSQL Connection Issues

If you get `Connection refused` errors

1. Check if PostgreSQL is running
   ```bash
   sudo systemctl status postgresql
   ```

2. Check PostgreSQL port
   ```bash
   sudo -u postgres psql -c "SHOW port;"
   ```

3. Update `POSTGRES_PORT` in `.env/test.sh` to match the actual port

### Import Errors

If you get `ModuleNotFoundError`

```bash
pip install django-environ django-configurations django-cors-headers psycopg2-binary
```

### Django Configuration Not Loading

Ensure environment variables are sourced

```bash
source .env/test.sh
echo $DJANGO_SETTINGS_MODULE
```
