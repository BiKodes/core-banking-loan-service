"""
Django App Configuration for Common Module

Registers the common app with its models and admin configuration.
"""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """
    Configuration for the 'common' Django app.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.common'
    verbose_name = 'Common / Multitenancy'
    
    def ready(self):
        """
        Initialize the app.
        
        This method is called when Django starts and all models are loaded.
        """
        from . import admin  # noqa: F401
