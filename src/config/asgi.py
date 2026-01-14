"""
ASGI config for core-banking-loan-service project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""
import os

from configurations.asgi import get_asgi_application


# Default to local environment if not explicitly set
DJANGO_ENV = os.getenv("DJANGO_ENV", "local").lower()

# Map environments to config modules
SETTINGS_MAP = {
    "local": "src.config.local",
    "production": "src.config.production",
}

# Set the correct config module based on DJANGO_ENV
os.environ.setdefault("DJANGO_SETTINGS_MODULE", SETTINGS_MAP.get(DJANGO_ENV, "src.config.local"))
os.environ.setdefault("DJANGO_CONFIGURATION", DJANGO_ENV.capitalize())


# Standard ASGI application (HTTP only; websockets removed)
application = get_asgi_application()
