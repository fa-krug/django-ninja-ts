"""Management command to manually generate TypeScript clients from Django Ninja schemas."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string
from openapi_ts_client import ClientFormat, generate_typescript_client

logger = logging.getLogger(__name__)

FORMAT_MAP = {
    "fetch": ClientFormat.FETCH,
    "axios": ClientFormat.AXIOS,
    "angular": ClientFormat.ANGULAR,
}


class SchemaValidationError(Exception):
    """Raised when the OpenAPI schema is invalid."""

    pass


class Command(BaseCommand):
    """Management command to generate TypeScript client from Django Ninja API."""

    help = "Generate TypeScript client from Django Ninja OpenAPI schema"

    def add_arguments(self, parser: Any) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force regeneration even if schema hasn't changed",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        api_path: str | None = getattr(settings, "NINJA_TS_API", None)
        output_dir: str | None = getattr(settings, "NINJA_TS_OUTPUT_DIR", None)

        if not api_path:
            raise CommandError(
                "NINJA_TS_API is not configured. "
                "Set it to a dot-notation import path like 'myapp.api.api'"
            )

        if not output_dir:
            raise CommandError(
                "NINJA_TS_OUTPUT_DIR is not configured. "
                "Set it to an absolute or relative path"
            )

        force = options.get("force", False)
        self._generate_client(api_path, output_dir, force)

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

    def _generate_client(self, api_path: str, output_dir: str, force: bool) -> None:
        """Generate the TypeScript client."""
        try:
            # Resolve paths
            output_dir = os.path.abspath(output_dir)
            hash_file = os.path.join(output_dir, ".schema.hash")

            # Load API
            logger.debug(f"Loading API from: {api_path}")
            api = import_string(api_path)

            # Get schema and validate
            if not hasattr(api, "get_openapi_schema"):
                raise CommandError(
                    f"API object at '{api_path}' does not have 'get_openapi_schema' method. "
                    "Ensure NINJA_TS_API points to a valid NinjaAPI instance."
                )

            schema_dict: dict[str, Any] = api.get_openapi_schema()
            self._validate_schema(schema_dict)

            # Calculate Hash using SHA256
            try:
                schema_str = json.dumps(schema_dict, sort_keys=True).encode("utf-8")
            except TypeError as e:
                raise CommandError(
                    f"Failed to serialize OpenAPI schema to JSON: {e}. "
                    "Ensure the schema contains only JSON-serializable types."
                ) from e

            new_hash = hashlib.sha256(schema_str).hexdigest()

            # Compare Hash (skip if force=True)
            if not force and not self._is_schema_changed(new_hash, hash_file):
                self.stdout.write("Schema unchanged, skipping generation")
                return

            self._run_generator(schema_dict, output_dir, hash_file, new_hash)

        except ModuleNotFoundError as e:
            raise CommandError(
                f"Module not found: {e}. Check that NINJA_TS_API path is correct."
            ) from e

        except SchemaValidationError as e:
            raise CommandError(str(e)) from e

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
        # Check output directory is writable
        parent_dir = os.path.dirname(output_dir) or "."
        if os.path.exists(parent_dir) and not os.access(parent_dir, os.W_OK):
            raise CommandError(f"Output directory parent is not writable: {parent_dir}")

        # Get format and clean settings
        format_name: str = getattr(settings, "NINJA_TS_FORMAT", "fetch")
        client_format = FORMAT_MAP[format_name]
        clean: bool = getattr(settings, "NINJA_TS_CLEAN", True)

        self.stdout.write(f"Generating {format_name} client to {output_dir}...")
        logger.info(f"Generating {format_name} TypeScript client to: {output_dir}")

        try:
            generate_typescript_client(
                openapi_spec=schema_dict,
                output_format=client_format,
                output_path=output_dir,
                clean=clean,
            )
        except ValueError as e:
            raise CommandError(f"Invalid OpenAPI spec: {e}") from e
        except OSError as e:
            raise CommandError(f"File system error during generation: {e}") from e

        # Save new hash
        os.makedirs(output_dir, exist_ok=True)
        with open(hash_file, "w") as f:
            f.write(new_hash)

        self.stdout.write(self.style.SUCCESS("Client generation successful."))
        logger.info("TypeScript client generation completed successfully")
