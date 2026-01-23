"""Django app configuration for django_ninja_ts."""

from __future__ import annotations

import logging
import os
from typing import Any

from django.apps import AppConfig
from django.core.checks import Error, Warning, register

logger = logging.getLogger(__name__)


class NinjaTsConfig(AppConfig):
    """Configuration for the Django Ninja TS app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_ninja_ts"
    verbose_name = "Django Ninja TypeScript Generator"

    def ready(self) -> None:
        """Validate configuration when Django starts."""
        # Register system checks
        register(check_ninja_ts_configuration)


def check_ninja_ts_configuration(
    app_configs: Any, **kwargs: Any
) -> list[Error | Warning]:
    """
    Django system check for django-ninja-ts configuration.

    This check validates that the configuration settings are valid
    before the server starts, providing early feedback to developers.
    """
    from django.conf import settings

    errors: list[Error | Warning] = []

    api_path: str | None = getattr(settings, "NINJA_TS_API", None)
    output_dir: str | None = getattr(settings, "NINJA_TS_OUTPUT_DIR", None)

    # If neither is configured, the feature is disabled - just log and return
    if not api_path and not output_dir:
        logger.debug("django-ninja-ts: No configuration found, feature disabled")
        return errors

    # Check NINJA_TS_API
    if api_path:
        if not isinstance(api_path, str):
            errors.append(
                Error(
                    "NINJA_TS_API must be a string",
                    hint="Set NINJA_TS_API to a dot-notation import path like 'myapp.api.api'",
                    id="ninja_ts.E001",
                )
            )
        elif not api_path.strip():
            errors.append(
                Error(
                    "NINJA_TS_API cannot be empty",
                    hint="Set NINJA_TS_API to a dot-notation import path like 'myapp.api.api'",
                    id="ninja_ts.E002",
                )
            )
        elif "." not in api_path:
            errors.append(
                Warning(
                    f"NINJA_TS_API '{api_path}' does not appear to be a valid import path",
                    hint="Import paths typically contain dots, e.g., 'myapp.api.api'",
                    id="ninja_ts.W001",
                )
            )
    elif output_dir:
        # output_dir is set but api_path is not
        errors.append(
            Error(
                "NINJA_TS_OUTPUT_DIR is set but NINJA_TS_API is not",
                hint="Both settings are required for TypeScript client generation",
                id="ninja_ts.E003",
            )
        )

    # Check NINJA_TS_OUTPUT_DIR
    if output_dir:
        if not isinstance(output_dir, str):
            errors.append(
                Error(
                    "NINJA_TS_OUTPUT_DIR must be a string",
                    hint="Set NINJA_TS_OUTPUT_DIR to an absolute or relative path",
                    id="ninja_ts.E004",
                )
            )
        elif not output_dir.strip():
            errors.append(
                Error(
                    "NINJA_TS_OUTPUT_DIR cannot be empty",
                    hint="Set NINJA_TS_OUTPUT_DIR to an absolute or relative path",
                    id="ninja_ts.E005",
                )
            )
        else:
            # Check if parent directory exists and is writable
            abs_output_dir = os.path.abspath(output_dir)
            parent_dir = os.path.dirname(abs_output_dir)
            if parent_dir and os.path.exists(parent_dir):
                if not os.access(parent_dir, os.W_OK):
                    errors.append(
                        Warning(
                            f"NINJA_TS_OUTPUT_DIR parent '{parent_dir}' is not writable",
                            hint="Ensure the parent directory exists and has write permissions",
                            id="ninja_ts.W002",
                        )
                    )
    elif api_path:
        # api_path is set but output_dir is not
        errors.append(
            Error(
                "NINJA_TS_API is set but NINJA_TS_OUTPUT_DIR is not",
                hint="Both settings are required for TypeScript client generation",
                id="ninja_ts.E006",
            )
        )

    # Check NINJA_TS_DEBOUNCE_SECONDS
    debounce = getattr(settings, "NINJA_TS_DEBOUNCE_SECONDS", None)
    if debounce is not None:
        if not isinstance(debounce, (int, float)):
            errors.append(
                Error(
                    "NINJA_TS_DEBOUNCE_SECONDS must be a number",
                    hint="Set NINJA_TS_DEBOUNCE_SECONDS to a float like 0.5 or 1.0",
                    id="ninja_ts.E007",
                )
            )
        elif debounce < 0:
            errors.append(
                Error(
                    "NINJA_TS_DEBOUNCE_SECONDS cannot be negative",
                    hint="Set NINJA_TS_DEBOUNCE_SECONDS to 0 or a positive number",
                    id="ninja_ts.E008",
                )
            )

    # Check NINJA_TS_FORMAT
    format_value = getattr(settings, "NINJA_TS_FORMAT", None)
    if format_value is not None:
        valid_formats = ["fetch", "axios", "angular"]
        if not isinstance(format_value, str):
            errors.append(
                Error(
                    "NINJA_TS_FORMAT must be a string",
                    hint=f"Set NINJA_TS_FORMAT to one of: {', '.join(valid_formats)}",
                    id="ninja_ts.E012",
                )
            )
        elif format_value not in valid_formats:
            errors.append(
                Error(
                    f"NINJA_TS_FORMAT '{format_value}' is not valid",
                    hint=f"Set NINJA_TS_FORMAT to one of: {', '.join(valid_formats)}",
                    id="ninja_ts.E011",
                )
            )

    # Check NINJA_TS_CLEAN
    clean_value = getattr(settings, "NINJA_TS_CLEAN", None)
    if clean_value is not None:
        if not isinstance(clean_value, bool):
            errors.append(
                Error(
                    "NINJA_TS_CLEAN must be a boolean",
                    hint="Set NINJA_TS_CLEAN to True or False",
                    id="ninja_ts.E013",
                )
            )

    return errors
