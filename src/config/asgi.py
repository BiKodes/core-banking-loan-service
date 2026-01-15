"""
ASGI config for core-banking-loan-service project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""
import os

from configurations.asgi import get_asgi_application


DJANGO_ENV = os.getenv("DJANGO_ENV", "local").lower()

SETTINGS_MAP = {
    "local": "src.config.local",
    "production": "src.config.production",
}

os.environ.setdefault("DJANGO_SETTINGS_MODULE", SETTINGS_MAP.get(DJANGO_ENV, "src.config.local"))
os.environ.setdefault("DJANGO_CONFIGURATION", DJANGO_ENV.capitalize())

application = get_asgi_application()
