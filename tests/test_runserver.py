"""Tests for the runserver management command."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from django_ninja_ts.management.commands.runserver import (
    Command,
    SchemaValidationError,
)


class TestCheckDependencies:
    """Tests for the _check_dependencies method."""

    def test_all_dependencies_present(self) -> None:
        """Test that True is returned when all dependencies are present."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/mock"
            result = command._check_dependencies()

        assert result is True

    def test_missing_node(self) -> None:
        """Test that False is returned when node is missing."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"
        command.style.WARNING = lambda x: f"WARNING: {x}"

        def which_side_effect(name: str) -> str | None:
            if name == "npx":
                return None
            return "/usr/bin/java"

        with patch("shutil.which", side_effect=which_side_effect):
            result = command._check_dependencies()

        assert result is False
        output = command.stdout.getvalue()
        assert "Node.js missing" in output

    def test_missing_java(self) -> None:
        """Test that False is returned when java is missing."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"
        command.style.WARNING = lambda x: f"WARNING: {x}"

        def which_side_effect(name: str) -> str | None:
            if name == "java":
                return None
            return "/usr/bin/npx"

        with patch("shutil.which", side_effect=which_side_effect):
            result = command._check_dependencies()

        assert result is False
        output = command.stdout.getvalue()
        assert "Java JRE missing" in output

    def test_missing_both_dependencies(self) -> None:
        """Test that False is returned when both dependencies are missing."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"
        command.style.WARNING = lambda x: f"WARNING: {x}"

        with patch("shutil.which", return_value=None):
            result = command._check_dependencies()

        assert result is False
        output = command.stdout.getvalue()
        assert "Node.js missing" in output
        assert "Java JRE missing" in output


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

    def test_hash_file_with_whitespace(self) -> None:
        """Test that whitespace in hash file is handled."""
        command = Command()

        with tempfile.TemporaryDirectory() as tmpdir:
            hash_file = os.path.join(tmpdir, ".schema.hash")
            with open(hash_file, "w") as f:
                f.write("  abc123  \n")

            result = command._is_schema_changed("abc123", hash_file)

        assert result is False

    def test_corrupted_hash_file(self) -> None:
        """Test that corrupted/unreadable hash file returns True."""
        command = Command()

        with tempfile.TemporaryDirectory() as tmpdir:
            hash_file = os.path.join(tmpdir, ".schema.hash")
            # Create a directory with the same name as the hash file
            os.makedirs(hash_file)

            result = command._is_schema_changed("abc123", hash_file)

        assert result is True


class TestDebounce:
    """Tests for the _debounce method."""

    def test_debounce_with_default_delay(self) -> None:
        """Test debounce with default delay setting."""
        command = Command()

        with patch("time.sleep"):
            with patch.object(
                type(command),
                "_debounce",
                lambda self: time.sleep(
                    getattr(
                        __import__("django.conf", fromlist=["settings"]).settings,
                        "NINJA_TS_DEBOUNCE_SECONDS",
                        1.0,
                    )
                ),
            ):
                pass
            # Just verify the method exists and is callable
            command._debounce()

    def test_debounce_respects_setting(self) -> None:
        """Test that debounce respects NINJA_TS_DEBOUNCE_SECONDS setting."""
        command = Command()

        with patch("time.sleep") as mock_sleep:
            with patch(
                "django.conf.settings.NINJA_TS_DEBOUNCE_SECONDS",
                0.5,
                create=True,
            ):
                command._debounce()
                mock_sleep.assert_called_once_with(0.5)

    def test_debounce_zero_delay(self) -> None:
        """Test that zero delay skips sleep."""
        command = Command()

        with patch("time.sleep") as mock_sleep:
            with patch(
                "django.conf.settings.NINJA_TS_DEBOUNCE_SECONDS",
                0,
                create=True,
            ):
                command._debounce()
                mock_sleep.assert_not_called()


class TestGenerateClient:
    """Tests for the _generate_client method."""

    def test_no_api_path_configured(self) -> None:
        """Test that generation is skipped when NINJA_TS_API is not set."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()

        with patch("django.conf.settings.NINJA_TS_API", None, create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                # Should return early without error
                command._generate_client()

        # No output expected
        assert command.stdout.getvalue() == ""

    def test_no_output_dir_configured(self) -> None:
        """Test that generation is skipped when NINJA_TS_OUTPUT_DIR is not set."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", None, create=True):
                # Should return early without error
                command._generate_client()

        # No output expected
        assert command.stdout.getvalue() == ""

    def test_import_error_handled(self) -> None:
        """Test that import errors are handled gracefully."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"

        with patch(
            "django.conf.settings.NINJA_TS_API", "nonexistent.module.api", create=True
        ):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                command._generate_client()

        output = command.stdout.getvalue()
        assert "ERROR:" in output

    def test_attribute_error_no_get_openapi_schema(self) -> None:
        """Test that AttributeError is raised when API lacks get_openapi_schema."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"

        mock_api = MagicMock(spec=[])  # No get_openapi_schema attribute

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch(
                    "django_ninja_ts.management.commands.runserver.import_string",
                    return_value=mock_api,
                ):
                    command._generate_client()

        output = command.stdout.getvalue()
        assert "ERROR:" in output
        assert "get_openapi_schema" in output

    def test_type_error_non_serializable_schema(self) -> None:
        """Test that TypeError is handled for non-JSON-serializable schemas."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"

        # Schema with non-serializable object
        mock_api = MagicMock()
        mock_api.get_openapi_schema.return_value = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "non_serializable": object(),  # This will cause TypeError
        }

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch(
                    "django_ninja_ts.management.commands.runserver.import_string",
                    return_value=mock_api,
                ):
                    command._generate_client()

        output = command.stdout.getvalue()
        assert "ERROR:" in output
        assert "serialize" in output.lower() or "json" in output.lower()


class TestSchemaValidation:
    """Tests for the _validate_schema method."""

    def test_valid_schema(self) -> None:
        """Test that valid schema passes validation."""
        command = Command()
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        # Should not raise
        command._validate_schema(schema)

    def test_missing_openapi_field(self) -> None:
        """Test that missing openapi field raises error."""
        command = Command()
        schema = {
            "info": {"title": "Test API"},
            "paths": {},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "openapi" in str(exc_info.value)

    def test_missing_info_field(self) -> None:
        """Test that missing info field raises error."""
        command = Command()
        schema = {
            "openapi": "3.0.0",
            "paths": {},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "info" in str(exc_info.value)

    def test_missing_paths_field(self) -> None:
        """Test that missing paths field raises error."""
        command = Command()
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "paths" in str(exc_info.value)

    def test_missing_title_in_info(self) -> None:
        """Test that missing title in info raises error."""
        command = Command()
        schema = {
            "openapi": "3.0.0",
            "info": {"version": "1.0.0"},
            "paths": {},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "title" in str(exc_info.value)

    def test_info_not_dict(self) -> None:
        """Test that non-dict info raises error."""
        command = Command()
        schema = {
            "openapi": "3.0.0",
            "info": "not a dict",
            "paths": {},
        }
        with pytest.raises(SchemaValidationError) as exc_info:
            command._validate_schema(schema)
        assert "title" in str(exc_info.value)


class TestRunGenerator:
    """Tests for the _run_generator method."""

    def test_successful_generation(self) -> None:
        """Test successful TypeScript client generation."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.SUCCESS = lambda x: f"SUCCESS: {x}"

        schema_dict: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            hash_file = os.path.join(output_dir, ".schema.hash")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

            # Verify hash file was written
            assert os.path.exists(hash_file)
            with open(hash_file) as f:
                assert f.read() == "abc123"

            output = command.stdout.getvalue()
            assert "SUCCESS:" in output

    def test_generation_failure(self) -> None:
        """Test handling of generation failure."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"

        schema_dict: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            hash_file = os.path.join(output_dir, ".schema.hash")

            with patch("subprocess.run") as mock_run:
                error = subprocess.CalledProcessError(1, "npx")
                error.stderr = b"Some error message"
                mock_run.side_effect = error
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

            # Verify hash file was NOT written on failure
            assert not os.path.exists(hash_file)

            output = command.stdout.getvalue()
            assert "ERROR:" in output

    def test_generation_failure_with_stderr(self) -> None:
        """Test that stderr is captured and logged on failure."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"

        schema_dict: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            hash_file = os.path.join(output_dir, ".schema.hash")

            with patch("subprocess.run") as mock_run:
                error = subprocess.CalledProcessError(1, "npx")
                error.stderr = b"Detailed error from generator"
                mock_run.side_effect = error
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

            output = command.stdout.getvalue()
            assert "Detailed error from generator" in output

    def test_temp_file_cleanup(self) -> None:
        """Test that temporary files are cleaned up after generation."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.SUCCESS = lambda x: f"SUCCESS: {x}"

        schema_dict: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        temp_files_created: list[str] = []

        original_named_temp = tempfile.NamedTemporaryFile

        def tracking_temp(*args: Any, **kwargs: Any) -> Any:
            result = original_named_temp(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            hash_file = os.path.join(output_dir, ".schema.hash")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
                with patch(
                    "tempfile.NamedTemporaryFile",
                    side_effect=tracking_temp,
                ):
                    command._run_generator(schema_dict, output_dir, hash_file, "abc123")

            # Verify temp file was cleaned up
            for temp_file in temp_files_created:
                assert not os.path.exists(temp_file)

    def test_timeout_handling(self) -> None:
        """Test that subprocess timeout is handled gracefully."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"

        schema_dict: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            hash_file = os.path.join(output_dir, ".schema.hash")

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("npx", 120)
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

            output = command.stdout.getvalue()
            assert "ERROR:" in output
            assert "timed out" in output.lower()

    def test_unwritable_output_directory(self) -> None:
        """Test that unwritable output directory is handled."""
        command = Command()
        command.stdout = StringIO()
        command.style = MagicMock()
        command.style.ERROR = lambda x: f"ERROR: {x}"
        command.style.SUCCESS = lambda x: f"SUCCESS: {x}"

        schema_dict: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            hash_file = os.path.join(output_dir, ".schema.hash")

            # Mock os.access to simulate unwritable directory
            with patch("os.access", return_value=False):
                with patch("os.path.exists", return_value=True):
                    command._run_generator(schema_dict, output_dir, hash_file, "abc123")

            output = command.stdout.getvalue()
            assert "ERROR:" in output
            assert "writable" in output.lower()


class TestCommandIntegration:
    """Integration tests for the Command class."""

    def test_command_inherits_from_runserver(self) -> None:
        """Test that Command inherits from Django's runserver command."""
        from django.core.management.commands.runserver import (
            Command as DjangoRunserver,
        )

        assert issubclass(Command, DjangoRunserver)

    def test_inner_run_calls_methods_in_order(self) -> None:
        """Test that inner_run calls methods in the correct order."""
        command = Command()
        call_order: list[str] = []

        def mock_debounce() -> None:
            call_order.append("debounce")

        def mock_check_deps() -> bool:
            call_order.append("check_deps")
            return True

        def mock_generate() -> None:
            call_order.append("generate")

        def mock_super_inner_run(*args: Any, **kwargs: Any) -> None:
            call_order.append("super_inner_run")

        command._debounce = mock_debounce  # type: ignore[method-assign]
        command._check_dependencies = mock_check_deps  # type: ignore[method-assign]
        command._generate_client = mock_generate  # type: ignore[method-assign]

        with patch.object(Command.__bases__[0], "inner_run", mock_super_inner_run):
            command.inner_run()

        assert call_order == ["debounce", "check_deps", "generate", "super_inner_run"]

    def test_skips_generation_when_deps_missing(self) -> None:
        """Test that generation is skipped when dependencies are missing."""
        command = Command()
        call_order: list[str] = []

        def mock_debounce() -> None:
            call_order.append("debounce")

        def mock_check_deps() -> bool:
            call_order.append("check_deps")
            return False  # Dependencies missing

        def mock_generate() -> None:
            call_order.append("generate")

        def mock_super_inner_run(*args: Any, **kwargs: Any) -> None:
            call_order.append("super_inner_run")

        command._debounce = mock_debounce  # type: ignore[method-assign]
        command._check_dependencies = mock_check_deps  # type: ignore[method-assign]
        command._generate_client = mock_generate  # type: ignore[method-assign]

        with patch.object(Command.__bases__[0], "inner_run", mock_super_inner_run):
            command.inner_run()

        # generate should NOT be in the call order
        assert call_order == ["debounce", "check_deps", "super_inner_run"]


class TestGetPlatform:
    """Tests for the _get_platform method."""

    def test_returns_lowercase_platform(self) -> None:
        """Test that platform is returned in lowercase."""
        command = Command()

        with patch("platform.system", return_value="Linux"):
            assert command._get_platform() == "linux"

        with patch("platform.system", return_value="Darwin"):
            assert command._get_platform() == "darwin"

        with patch("platform.system", return_value="Windows"):
            assert command._get_platform() == "windows"


class TestConfigurationCheck:
    """Tests for the configuration validation check."""

    def test_no_config_returns_empty(self) -> None:
        """Test that no configuration returns no errors."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", None, create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", None, create=True):
                errors = check_ninja_ts_configuration(None)
                assert errors == []

    def test_api_path_not_string(self) -> None:
        """Test that non-string NINJA_TS_API raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", 123, create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp", create=True):
                errors = check_ninja_ts_configuration(None)
                assert len(errors) >= 1
                assert any("E001" in str(e.id) for e in errors)

    def test_api_path_empty(self) -> None:
        """Test that empty NINJA_TS_API raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "   ", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp", create=True):
                errors = check_ninja_ts_configuration(None)
                assert len(errors) >= 1
                assert any("E002" in str(e.id) for e in errors)

    def test_api_path_no_dots_warning(self) -> None:
        """Test that NINJA_TS_API without dots raises warning."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp", create=True):
                errors = check_ninja_ts_configuration(None)
                assert len(errors) >= 1
                assert any("W001" in str(e.id) for e in errors)

    def test_output_dir_without_api_path(self) -> None:
        """Test that output_dir without api_path raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", None, create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp", create=True):
                errors = check_ninja_ts_configuration(None)
                assert len(errors) >= 1
                assert any("E003" in str(e.id) for e in errors)

    def test_api_path_without_output_dir(self) -> None:
        """Test that api_path without output_dir raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", None, create=True):
                errors = check_ninja_ts_configuration(None)
                assert len(errors) >= 1
                assert any("E006" in str(e.id) for e in errors)

    def test_debounce_not_number(self) -> None:
        """Test that non-numeric debounce raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp", create=True):
                with patch(
                    "django.conf.settings.NINJA_TS_DEBOUNCE_SECONDS",
                    "not a number",
                    create=True,
                ):
                    errors = check_ninja_ts_configuration(None)
                    assert any("E007" in str(e.id) for e in errors)

    def test_debounce_negative(self) -> None:
        """Test that negative debounce raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp", create=True):
                with patch(
                    "django.conf.settings.NINJA_TS_DEBOUNCE_SECONDS",
                    -1.0,
                    create=True,
                ):
                    errors = check_ninja_ts_configuration(None)
                    assert any("E008" in str(e.id) for e in errors)

    def test_format_valid_values(self) -> None:
        """Test that valid NINJA_TS_FORMAT values are accepted."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        for format_value in ["fetch", "axios", "angular"]:
            with patch(
                "django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True
            ):
                with patch(
                    "django.conf.settings.NINJA_TS_OUTPUT_DIR",
                    "/tmp/output",
                    create=True,
                ):
                    with patch(
                        "django.conf.settings.NINJA_TS_FORMAT",
                        format_value,
                        create=True,
                    ):
                        errors = check_ninja_ts_configuration(None)
                        assert not any(
                            "ninja_ts" in str(e.id) and "FORMAT" in str(e.msg).upper()
                            for e in errors
                        ), f"Format '{format_value}' should be valid"

    def test_format_invalid_value(self) -> None:
        """Test that invalid NINJA_TS_FORMAT raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch(
                    "django.conf.settings.NINJA_TS_FORMAT", "invalid", create=True
                ):
                    errors = check_ninja_ts_configuration(None)
                    assert any("E011" in str(e.id) for e in errors)

    def test_format_not_string(self) -> None:
        """Test that non-string NINJA_TS_FORMAT raises error."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch("django.conf.settings.NINJA_TS_FORMAT", 123, create=True):
                    errors = check_ninja_ts_configuration(None)
                    assert any("E012" in str(e.id) for e in errors)

    def test_valid_configuration(self) -> None:
        """Test that valid configuration returns no errors."""
        from django_ninja_ts.apps import check_ninja_ts_configuration

        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch(
                "django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True
            ):
                with patch(
                    "django.conf.settings.NINJA_TS_DEBOUNCE_SECONDS",
                    0.5,
                    create=True,
                ):
                    with patch(
                        "django.conf.settings.NINJA_TS_FORMAT",
                        "fetch",
                        create=True,
                    ):
                        errors = check_ninja_ts_configuration(None)
                        assert errors == []
