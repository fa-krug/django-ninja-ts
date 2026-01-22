"""Django app configuration for django_ninja_ts."""

from django.apps import AppConfig


class NinjaTsConfig(AppConfig):
    """Configuration for the Django Ninja TS app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_ninja_ts"
    verbose_name = "Django Ninja TypeScript Generator"
