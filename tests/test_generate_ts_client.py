"""Tests for the generate_ts_client management command."""

from __future__ import annotations

import os
import tempfile
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from django_ninja_ts.management.commands.generate_ts_client import Command


class TestGenerateTsClientCommand:
    """Tests for the generate_ts_client management command."""

    def test_missing_ninja_ts_api(self) -> None:
        """Test that CommandError is raised when NINJA_TS_API is not configured."""
        with patch("django.conf.settings.NINJA_TS_API", None, create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with pytest.raises(CommandError) as exc_info:
                    call_command("generate_ts_client")
                assert "NINJA_TS_API is not configured" in str(exc_info.value)

    def test_missing_ninja_ts_output_dir(self) -> None:
        """Test that CommandError is raised when NINJA_TS_OUTPUT_DIR is not configured."""
        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", None, create=True):
                with pytest.raises(CommandError) as exc_info:
                    call_command("generate_ts_client")
                assert "NINJA_TS_OUTPUT_DIR is not configured" in str(exc_info.value)

    def test_module_not_found(self) -> None:
        """Test that CommandError is raised when API module is not found."""
        with patch(
            "django.conf.settings.NINJA_TS_API", "nonexistent.module.api", create=True
        ):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with pytest.raises(CommandError) as exc_info:
                    call_command("generate_ts_client")
                assert "Module not found" in str(exc_info.value)

    def test_api_without_get_openapi_schema(self) -> None:
        """Test that CommandError is raised when API lacks get_openapi_schema."""
        mock_api = MagicMock(spec=[])

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch(
                    "django_ninja_ts.management.commands.generate_ts_client.import_string",
                    return_value=mock_api,
                ):
                    with pytest.raises(CommandError) as exc_info:
                        call_command("generate_ts_client")
                    assert "get_openapi_schema" in str(exc_info.value)

    def test_schema_unchanged_skips_generation(self) -> None:
        """Test that generation is skipped when schema hasn't changed."""
        mock_api = MagicMock()
        mock_api.get_openapi_schema.return_value = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = tmpdir
            hash_file = os.path.join(output_dir, ".schema.hash")

            # Pre-create hash file with correct hash
            import hashlib
            import json

            schema_str = json.dumps(
                mock_api.get_openapi_schema.return_value, sort_keys=True
            ).encode("utf-8")
            correct_hash = hashlib.sha256(schema_str).hexdigest()
            with open(hash_file, "w") as f:
                f.write(correct_hash)

            with patch(
                "django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True
            ):
                with patch(
                    "django.conf.settings.NINJA_TS_OUTPUT_DIR", output_dir, create=True
                ):
                    with patch(
                        "django_ninja_ts.management.commands.generate_ts_client.import_string",
                        return_value=mock_api,
                    ):
                        with patch(
                            "django_ninja_ts.management.commands.generate_ts_client.generate_typescript_client"
                        ) as mock_generate:
                            out = StringIO()
                            call_command("generate_ts_client", stdout=out)

                            # Generation should NOT have been called
                            mock_generate.assert_not_called()
                            assert "unchanged" in out.getvalue()

    def test_force_regenerates_even_if_unchanged(self) -> None:
        """Test that --force regenerates even when schema hasn't changed."""
        mock_api = MagicMock()
        mock_api.get_openapi_schema.return_value = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = tmpdir
            hash_file = os.path.join(output_dir, ".schema.hash")

            # Pre-create hash file with correct hash
            import hashlib
            import json

            schema_str = json.dumps(
                mock_api.get_openapi_schema.return_value, sort_keys=True
            ).encode("utf-8")
            correct_hash = hashlib.sha256(schema_str).hexdigest()
            with open(hash_file, "w") as f:
                f.write(correct_hash)

            with patch(
                "django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True
            ):
                with patch(
                    "django.conf.settings.NINJA_TS_OUTPUT_DIR", output_dir, create=True
                ):
                    with patch(
                        "django_ninja_ts.management.commands.generate_ts_client.import_string",
                        return_value=mock_api,
                    ):
                        with patch(
                            "django_ninja_ts.management.commands.generate_ts_client.generate_typescript_client"
                        ) as mock_generate:
                            out = StringIO()
                            call_command("generate_ts_client", "--force", stdout=out)

                            # Generation SHOULD have been called
                            mock_generate.assert_called_once()

    def test_successful_generation(self) -> None:
        """Test successful TypeScript client generation."""
        mock_api = MagicMock()
        mock_api.get_openapi_schema.return_value = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")

            with patch(
                "django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True
            ):
                with patch(
                    "django.conf.settings.NINJA_TS_OUTPUT_DIR", output_dir, create=True
                ):
                    with patch(
                        "django.conf.settings.NINJA_TS_FORMAT", "fetch", create=True
                    ):
                        with patch(
                            "django_ninja_ts.management.commands.generate_ts_client.import_string",
                            return_value=mock_api,
                        ):
                            with patch(
                                "django_ninja_ts.management.commands.generate_ts_client.generate_typescript_client"
                            ) as mock_generate:
                                out = StringIO()
                                call_command("generate_ts_client", stdout=out)

                                mock_generate.assert_called_once()
                                assert "successful" in out.getvalue().lower()

                                # Hash file should be created
                                hash_file = os.path.join(output_dir, ".schema.hash")
                                assert os.path.exists(hash_file)

    def test_invalid_schema(self) -> None:
        """Test that CommandError is raised for invalid schema."""
        mock_api = MagicMock()
        mock_api.get_openapi_schema.return_value = {
            "info": {"title": "Test API"},  # Missing openapi and paths
        }

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch(
                    "django_ninja_ts.management.commands.generate_ts_client.import_string",
                    return_value=mock_api,
                ):
                    with pytest.raises(CommandError) as exc_info:
                        call_command("generate_ts_client")
                    assert "Invalid OpenAPI schema" in str(exc_info.value)


class TestIsSchemaChanged:
    """Tests for the _is_schema_changed method."""

    def test_no_hash_file_exists(self) -> None:
        """Test that True is returned when hash file doesn't exist."""
        command = Command()

        with tempfile.TemporaryDirectory() as tmpdir:
            hash_file = os.path.join(tmpdir, ".schema.hash")
            result = command._is_schema_changed("abc123", hash_file)

        assert result is True

    def test_hash_matches(self) -> None:
        """Test that False is returned when hash matches."""
        command = Command()

        with tempfile.TemporaryDirectory() as tmpdir:
            hash_file = os.path.join(tmpdir, ".schema.hash")
            with open(hash_file, "w") as f:
                f.write("abc123")

            result = command._is_schema_changed("abc123", hash_file)

        assert result is False

    def test_hash_differs(self) -> None:
        """Test that True is returned when hash differs."""
        command = Command()

        with tempfile.TemporaryDirectory() as tmpdir:
            hash_file = os.path.join(tmpdir, ".schema.hash")
            with open(hash_file, "w") as f:
                f.write("abc123")

            result = command._is_schema_changed("xyz789", hash_file)

        assert result is True


class TestValidateSchema:
    """Tests for the _validate_schema method."""

    def test_valid_schema(self) -> None:
        """Test that valid schema passes validation."""
        command = Command()
        schema: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        # Should not raise
        command._validate_schema(schema)

    def test_missing_openapi_field(self) -> None:
        """Test that missing openapi field raises error."""
        from django_ninja_ts.management.commands.generate_ts_client import (
            SchemaValidationError,
        )

        command = Command()
        schema: dict[str, Any] = {
            "info": {"title": "Test API"},
            "paths": {},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "openapi" in str(exc_info.value)

    def test_missing_title_in_info(self) -> None:
        """Test that missing title in info raises error."""
        from django_ninja_ts.management.commands.generate_ts_client import (
            SchemaValidationError,
        )

        command = Command()
        schema: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"version": "1.0.0"},
            "paths": {},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "title" in str(exc_info.value)
