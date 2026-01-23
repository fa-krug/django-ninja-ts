"""Custom runserver command that generates TypeScript clients from Django Ninja schemas."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, TypedDict

from django.conf import settings
from django.core.management.commands.runserver import Command as RunserverCommand
from django.utils.module_loading import import_string
from openapi_ts_client import ClientFormat, generate_typescript_client

logger = logging.getLogger(__name__)

FORMAT_MAP = {
    "fetch": ClientFormat.FETCH,
    "axios": ClientFormat.AXIOS,
    "angular": ClientFormat.ANGULAR,
}


class OpenAPIInfo(TypedDict, total=False):
    """TypedDict for OpenAPI info object."""

    title: str
    version: str
    description: str


class OpenAPISchema(TypedDict, total=False):
    """TypedDict for OpenAPI schema structure."""

    openapi: str
    info: OpenAPIInfo
    paths: dict[str, Any]
    components: dict[str, Any]
    servers: list[dict[str, Any]]
    tags: list[dict[str, Any]]


class SchemaValidationError(Exception):
    """Raised when the OpenAPI schema is invalid."""

    pass


class Command(RunserverCommand):
    """Extended runserver command that auto-generates TypeScript clients."""

    def inner_run(self, *args: Any, **options: Any) -> None:
        """Run the server with TypeScript client generation."""
        # 1. Debounce (Wait for rapid file saves to settle)
        self._debounce()

        # 2. Run generation
        self._generate_client()

        # 3. Start the actual Django server
        super().inner_run(*args, **options)

    def _debounce(self) -> None:
        """
        Sleep briefly to let the auto-reloader kill this process.

        This handles the case where a subsequent file change occurs
        immediately (e.g. 'Save All').
        """
        delay: float = getattr(settings, "NINJA_TS_DEBOUNCE_SECONDS", 1.0)
        if delay > 0:
            time.sleep(delay)

    def _validate_schema(self, schema: dict[str, Any]) -> None:
        """
        Validate that the schema is a valid OpenAPI schema.

        Args:
            schema: The schema dictionary to validate.

        Raises:
            SchemaValidationError: If the schema is missing required fields.
        """
        required_fields = ["openapi", "info", "paths"]
        missing_fields = [field for field in required_fields if field not in schema]

        if missing_fields:
            raise SchemaValidationError(
                f"Invalid OpenAPI schema: missing required fields: {', '.join(missing_fields)}"
            )

        # Validate info has required title field
        info = schema.get("info", {})
        if not isinstance(info, dict) or "title" not in info:
            raise SchemaValidationError(
                "Invalid OpenAPI schema: 'info' must contain 'title'"
            )

    def _generate_client(self) -> None:
        """Generate the TypeScript client if the schema has changed."""
        api_path: str | None = getattr(settings, "NINJA_TS_API", None)
        output_dir: str | None = getattr(settings, "NINJA_TS_OUTPUT_DIR", None)

        if not api_path or not output_dir:
            logger.debug(
                "TypeScript client generation skipped: NINJA_TS_API or NINJA_TS_OUTPUT_DIR not configured"
            )
            return

        try:
            # Resolve paths
            output_dir = os.path.abspath(output_dir)
            hash_file = os.path.join(output_dir, ".schema.hash")

            # Load API
            logger.debug(f"Loading API from: {api_path}")
            api = import_string(api_path)

            # Get schema and validate
            if not hasattr(api, "get_openapi_schema"):
                raise AttributeError(
                    f"API object at '{api_path}' does not have 'get_openapi_schema' method. "
                    "Ensure NINJA_TS_API points to a valid NinjaAPI instance."
                )

            schema_dict: dict[str, Any] = api.get_openapi_schema()
            self._validate_schema(schema_dict)

            # Calculate Hash using SHA256
            try:
                schema_str = json.dumps(schema_dict, sort_keys=True).encode("utf-8")
            except TypeError as e:
                raise TypeError(
                    f"Failed to serialize OpenAPI schema to JSON: {e}. "
                    "Ensure the schema contains only JSON-serializable types."
                ) from e

            new_hash = hashlib.sha256(schema_str).hexdigest()

            # Compare Hash
            if self._is_schema_changed(new_hash, hash_file):
                self._run_generator(schema_dict, output_dir, hash_file, new_hash)
            else:
                logger.debug("Schema unchanged, skipping generation")

        except ModuleNotFoundError as e:
            error_msg = (
                f"Module not found: {e}. Check that NINJA_TS_API path is correct."
            )
            self.stdout.write(self.style.ERROR(f"Generation Error: {error_msg}"))
            logger.error(error_msg)

        except AttributeError as e:
            error_msg = str(e)
            self.stdout.write(self.style.ERROR(f"Generation Error: {error_msg}"))
            logger.error(error_msg)

        except SchemaValidationError as e:
            error_msg = str(e)
            self.stdout.write(self.style.ERROR(f"Generation Error: {error_msg}"))
            logger.error(error_msg)

        except TypeError as e:
            error_msg = str(e)
            self.stdout.write(self.style.ERROR(f"Generation Error: {error_msg}"))
            logger.error(error_msg)

        except OSError as e:
            error_msg = f"File system error: {e}"
            self.stdout.write(self.style.ERROR(f"Generation Error: {error_msg}"))
            logger.error(error_msg)

    def _is_schema_changed(self, new_hash: str, hash_file: str) -> bool:
        """Check if the schema has changed since last generation."""
        if not os.path.exists(hash_file):
            return True
        try:
            with open(hash_file) as f:
                return f.read().strip() != new_hash
        except OSError:
            return True

    def _run_generator(
        self,
        schema_dict: dict[str, Any],
        output_dir: str,
        hash_file: str,
        new_hash: str,
    ) -> None:
        """Run the TypeScript client generator."""
        try:
            # Check output directory is writable
            parent_dir = os.path.dirname(output_dir) or "."
            if os.path.exists(parent_dir) and not os.access(parent_dir, os.W_OK):
                raise OSError(f"Output directory parent is not writable: {parent_dir}")

            # Get format and clean settings
            format_name: str = getattr(settings, "NINJA_TS_FORMAT", "fetch")
            client_format = FORMAT_MAP[format_name]
            clean: bool = getattr(settings, "NINJA_TS_CLEAN", True)

            self.stdout.write(f"Generating {format_name} client to {output_dir}...")
            logger.info(f"Generating {format_name} TypeScript client to: {output_dir}")

            generate_typescript_client(
                openapi_spec=schema_dict,
                output_format=client_format,
                output_path=output_dir,
                clean=clean,
            )

            # Save new hash
            os.makedirs(output_dir, exist_ok=True)
            with open(hash_file, "w") as f:
                f.write(new_hash)

            self.stdout.write(self.style.SUCCESS("Client generation successful."))
            logger.info("TypeScript client generation completed successfully")

        except ValueError as e:
            error_msg = f"Invalid OpenAPI spec: {e}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)

        except OSError as e:
            error_msg = f"File system error during generation: {e}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
