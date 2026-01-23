# openapi-ts-client Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace openapi-generator-cli (Node.js/Java) with openapi-ts-client (pure Python) for TypeScript client generation.

**Architecture:** Remove subprocess-based generation, replace with direct Python API call to `generate_typescript_client()`. Remove dependency checks for Node.js/Java. Replace `NINJA_TS_CMD_ARGS` with `NINJA_TS_FORMAT`.

**Tech Stack:** Python 3.8+, Django, openapi-ts-client

---

## Task 1: Add openapi-ts-client Dependency

**Files:**
- Modify: `pyproject.toml:37-40`

**Step 1: Update dependencies**

Add `openapi-ts-client>=1.0.0` to the dependencies list:

```toml
dependencies = [
    "Django>=4.0",
    "django-ninja>=1.0",
    "openapi-ts-client>=1.0.0",
]
```

**Step 2: Install updated dependencies**

Run: `pip3 install -e ".[dev]"`
Expected: Successfully installed openapi-ts-client

**Step 3: Verify import works**

Run: `python3 -c "from openapi_ts_client import generate_typescript_client, ClientFormat; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): add openapi-ts-client dependency"
```

---

## Task 2: Update System Check for NINJA_TS_FORMAT

**Files:**
- Modify: `django_ninja_ts/apps.py:146-164`
- Test: `tests/test_runserver.py`

**Step 1: Write the failing test for valid NINJA_TS_FORMAT**

Add to `tests/test_runserver.py` in class `TestConfigurationCheck`:

```python
def test_format_valid_values(self) -> None:
    """Test that valid NINJA_TS_FORMAT values are accepted."""
    from django_ninja_ts.apps import check_ninja_ts_configuration

    for format_value in ["fetch", "axios", "angular"]:
        with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
            with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True):
                with patch("django.conf.settings.NINJA_TS_FORMAT", format_value, create=True):
                    errors = check_ninja_ts_configuration(None)
                    assert not any("ninja_ts" in str(e.id) and "FORMAT" in str(e.msg).upper() for e in errors), f"Format '{format_value}' should be valid"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runserver.py::TestConfigurationCheck::test_format_valid_values -v`
Expected: FAIL (NINJA_TS_FORMAT not yet validated)

**Step 3: Write the failing test for invalid NINJA_TS_FORMAT**

Add to `tests/test_runserver.py` in class `TestConfigurationCheck`:

```python
def test_format_invalid_value(self) -> None:
    """Test that invalid NINJA_TS_FORMAT raises error."""
    from django_ninja_ts.apps import check_ninja_ts_configuration

    with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
        with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True):
            with patch("django.conf.settings.NINJA_TS_FORMAT", "invalid", create=True):
                errors = check_ninja_ts_configuration(None)
                assert any("E011" in str(e.id) for e in errors)


def test_format_not_string(self) -> None:
    """Test that non-string NINJA_TS_FORMAT raises error."""
    from django_ninja_ts.apps import check_ninja_ts_configuration

    with patch("django.conf.settings.NINJA_TS_API", "myapp.api.api", create=True):
        with patch("django.conf.settings.NINJA_TS_OUTPUT_DIR", "/tmp/output", create=True):
            with patch("django.conf.settings.NINJA_TS_FORMAT", 123, create=True):
                errors = check_ninja_ts_configuration(None)
                assert any("E012" in str(e.id) for e in errors)
```

**Step 4: Run tests to verify they fail**

Run: `pytest tests/test_runserver.py::TestConfigurationCheck::test_format_invalid_value tests/test_runserver.py::TestConfigurationCheck::test_format_not_string -v`
Expected: FAIL

**Step 5: Replace NINJA_TS_CMD_ARGS validation with NINJA_TS_FORMAT validation**

In `django_ninja_ts/apps.py`, replace lines 146-164:

```python
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

    return errors
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_runserver.py::TestConfigurationCheck -v`
Expected: PASS

**Step 7: Remove old CMD_ARGS tests**

Remove these test methods from `TestConfigurationCheck`:
- `test_cmd_args_not_list`
- `test_cmd_args_contains_non_string`

Update `test_valid_configuration` to use `NINJA_TS_FORMAT` instead of `NINJA_TS_CMD_ARGS`:

```python
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
```

**Step 8: Run all configuration tests**

Run: `pytest tests/test_runserver.py::TestConfigurationCheck -v`
Expected: PASS

**Step 9: Commit**

```bash
git add django_ninja_ts/apps.py tests/test_runserver.py
git commit -m "feat(config): replace NINJA_TS_CMD_ARGS with NINJA_TS_FORMAT"
```

---

## Task 3: Remove Dependency Check Methods and Tests

**Files:**
- Modify: `django_ninja_ts/management/commands/runserver.py:77-121`
- Modify: `tests/test_runserver.py`

**Step 1: Remove TestCheckDependencies test class**

Delete the entire `TestCheckDependencies` class (lines 21-91 approximately) from `tests/test_runserver.py`.

**Step 2: Remove TestGetPlatform test class**

Delete the entire `TestGetPlatform` class from `tests/test_runserver.py`.

**Step 3: Run remaining tests to ensure no breakage**

Run: `pytest tests/test_runserver.py -v`
Expected: PASS (fewer tests now)

**Step 4: Remove _check_dependencies method from runserver.py**

Delete the `_check_dependencies` method (lines 81-121) from `runserver.py`.

**Step 5: Remove _get_platform method from runserver.py**

Delete the `_get_platform` method (lines 77-79) from `runserver.py`.

**Step 6: Remove unused imports from runserver.py**

Remove these imports from the top of `runserver.py`:
- `platform`
- `shutil`
- `subprocess`

**Step 7: Update inner_run to remove dependency check**

Change the `inner_run` method to:

```python
def inner_run(self, *args: Any, **options: Any) -> None:
    """Run the server with TypeScript client generation."""
    # 1. Debounce (Wait for rapid file saves to settle)
    self._debounce()

    # 2. Run generation
    self._generate_client()

    # 3. Start the actual Django server
    super().inner_run(*args, **options)
```

**Step 8: Update TestCommandIntegration tests**

Update `test_inner_run_calls_methods_in_order`:

```python
def test_inner_run_calls_methods_in_order(self) -> None:
    """Test that inner_run calls methods in the correct order."""
    command = Command()
    call_order: list[str] = []

    def mock_debounce() -> None:
        call_order.append("debounce")

    def mock_generate() -> None:
        call_order.append("generate")

    def mock_super_inner_run(*args: Any, **kwargs: Any) -> None:
        call_order.append("super_inner_run")

    command._debounce = mock_debounce  # type: ignore[method-assign]
    command._generate_client = mock_generate  # type: ignore[method-assign]

    with patch.object(Command.__bases__[0], "inner_run", mock_super_inner_run):
        command.inner_run()

    assert call_order == ["debounce", "generate", "super_inner_run"]
```

Remove `test_skips_generation_when_deps_missing` test entirely.

**Step 9: Run tests**

Run: `pytest tests/test_runserver.py -v`
Expected: PASS

**Step 10: Commit**

```bash
git add django_ninja_ts/management/commands/runserver.py tests/test_runserver.py
git commit -m "refactor(runserver): remove Node.js/Java dependency checks"
```

---

## Task 4: Replace Subprocess Generator with openapi-ts-client

**Files:**
- Modify: `django_ninja_ts/management/commands/runserver.py`
- Modify: `tests/test_runserver.py`

**Step 1: Write failing test for successful generation with openapi-ts-client**

Replace `TestRunGenerator.test_successful_generation`:

```python
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

        with patch("django.conf.settings.NINJA_TS_FORMAT", "fetch", create=True):
            with patch(
                "django_ninja_ts.management.commands.runserver.generate_typescript_client"
            ) as mock_generate:
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

        # Verify generate_typescript_client was called correctly
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args
        assert call_kwargs[1]["openapi_spec"] == schema_dict
        assert call_kwargs[1]["output_path"] == output_dir

        # Verify hash file was written
        assert os.path.exists(hash_file)
        with open(hash_file) as f:
            assert f.read() == "abc123"

        output = command.stdout.getvalue()
        assert "SUCCESS:" in output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runserver.py::TestRunGenerator::test_successful_generation -v`
Expected: FAIL (generate_typescript_client not imported)

**Step 3: Add imports to runserver.py**

Add at the top of `runserver.py`:

```python
from openapi_ts_client import ClientFormat, generate_typescript_client
```

**Step 4: Add FORMAT_MAP constant**

Add after the `GENERATOR_TIMEOUT` constant (which can be removed):

```python
FORMAT_MAP = {
    "fetch": ClientFormat.FETCH,
    "axios": ClientFormat.AXIOS,
    "angular": ClientFormat.ANGULAR,
}
```

**Step 5: Replace _run_generator method**

Replace the entire `_run_generator` method with:

```python
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

        # Get format from settings
        format_name: str = getattr(settings, "NINJA_TS_FORMAT", "fetch")
        client_format = FORMAT_MAP[format_name]

        self.stdout.write(f"Generating {format_name} client to {output_dir}...")
        logger.info(f"Generating {format_name} TypeScript client to: {output_dir}")

        generate_typescript_client(
            openapi_spec=schema_dict,
            output_format=client_format,
            output_path=output_dir,
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
```

**Step 6: Remove unused imports and constants**

Remove from `runserver.py`:
- `import tempfile`
- `GENERATOR_TIMEOUT = 120`

**Step 7: Run test to verify it passes**

Run: `pytest tests/test_runserver.py::TestRunGenerator::test_successful_generation -v`
Expected: PASS

**Step 8: Update test_generation_failure**

Replace with:

```python
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

        with patch("django.conf.settings.NINJA_TS_FORMAT", "fetch", create=True):
            with patch(
                "django_ninja_ts.management.commands.runserver.generate_typescript_client"
            ) as mock_generate:
                mock_generate.side_effect = ValueError("Invalid spec")
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

        # Verify hash file was NOT written on failure
        assert not os.path.exists(hash_file)

        output = command.stdout.getvalue()
        assert "ERROR:" in output
```

**Step 9: Remove obsolete tests from TestRunGenerator**

Delete these tests:
- `test_generation_failure_with_stderr`
- `test_temp_file_cleanup`
- `test_timeout_handling`

Keep `test_unwritable_output_directory` but update it:

```python
def test_unwritable_output_directory(self) -> None:
    """Test that unwritable output directory is handled."""
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

        # Mock os.access to simulate unwritable directory
        with patch("os.access", return_value=False):
            with patch("os.path.exists", return_value=True):
                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

        output = command.stdout.getvalue()
        assert "ERROR:" in output
        assert "writable" in output.lower()
```

**Step 10: Add test for different formats**

```python
def test_generation_with_axios_format(self) -> None:
    """Test generation with axios format."""
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

        with patch("django.conf.settings.NINJA_TS_FORMAT", "axios", create=True):
            with patch(
                "django_ninja_ts.management.commands.runserver.generate_typescript_client"
            ) as mock_generate:
                from openapi_ts_client import ClientFormat

                command._run_generator(schema_dict, output_dir, hash_file, "abc123")

                # Verify correct format was used
                call_kwargs = mock_generate.call_args
                assert call_kwargs[1]["output_format"] == ClientFormat.AXIOS
```

**Step 11: Remove subprocess import from tests**

Remove `import subprocess` from `tests/test_runserver.py`.

**Step 12: Run all tests**

Run: `pytest tests/test_runserver.py -v`
Expected: PASS

**Step 13: Run linter**

Run: `ruff check .`
Expected: No errors

**Step 14: Commit**

```bash
git add django_ninja_ts/management/commands/runserver.py tests/test_runserver.py
git commit -m "feat(generator): use openapi-ts-client instead of subprocess"
```

---

## Task 5: Bump Version to 2.0.0

**Files:**
- Modify: `django_ninja_ts/__init__.py`

**Step 1: Update version**

Change the version in `django_ninja_ts/__init__.py` to:

```python
__version__ = "2.0.0"
```

**Step 2: Verify version**

Run: `python3 -c "import django_ninja_ts; print(django_ninja_ts.__version__)"`
Expected: `2.0.0`

**Step 3: Commit**

```bash
git add django_ninja_ts/__init__.py
git commit -m "chore(release): bump version to 2.0.0"
```

---

## Task 6: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Add migration section at top (after Installation)**

Add after the Installation section:

```markdown
## Migrating from v1.x

v2.0 switched from `openapi-generator-cli` (Node.js/Java) to `openapi-ts-client` (pure Python).

**Breaking changes:**
- Remove `NINJA_TS_CMD_ARGS` from your settings (no longer supported)
- Add `NINJA_TS_FORMAT` if you need axios or angular (fetch is default)
- Node.js and Java are no longer required
```

**Step 2: Remove Requirements section**

Delete the entire "Requirements" section that mentions Node.js and Java.

**Step 3: Update Configuration section**

Replace the Configuration example with:

```python
import os

# Path to your NinjaAPI instance (dot notation)
NINJA_TS_API = 'myproject.api.api'

# Where to output the generated client
NINJA_TS_OUTPUT_DIR = os.path.join(BASE_DIR, '../frontend/src/app/shared/api')

# Optional: Client format - 'fetch' (default), 'axios', or 'angular'
NINJA_TS_FORMAT = 'fetch'

# Optional: Debounce time in seconds (prevents rapid rebuilds on "Save All")
# Default: 1.0
# NINJA_TS_DEBOUNCE_SECONDS = 0.5
```

**Step 4: Update Configuration Options table**

Replace the table with:

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `NINJA_TS_API` | Yes | - | Dot-notation path to your NinjaAPI instance |
| `NINJA_TS_OUTPUT_DIR` | Yes | - | Directory where the TypeScript client will be generated |
| `NINJA_TS_FORMAT` | No | `fetch` | Client format: `fetch`, `axios`, or `angular` |
| `NINJA_TS_DEBOUNCE_SECONDS` | No | `1.0` | Delay before generation to handle rapid file saves |

**Step 5: Remove "Default Generator Arguments" section**

Delete the entire section about default generator arguments.

**Step 6: Update format examples**

Replace "Example: Using Axios" and "Example: Using Angular" with:

```markdown
### Example: Using Axios

```python
NINJA_TS_FORMAT = 'axios'
```

### Example: Using Angular

```python
NINJA_TS_FORMAT = 'angular'
```
```

**Step 7: Update Troubleshooting section**

Remove these subsections:
- "Generation hangs indefinitely"
- "Windows-specific issues"

**Step 8: Commit**

```bash
git add README.md
git commit -m "docs: update README for v2.0 migration"
```

---

## Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Architecture section**

Replace the Generation Flow with:

```markdown
**Generation Flow (`runserver.py`):**
1. Debounce rapid file saves (configurable delay)
2. Load NinjaAPI from configured Django settings path
3. Get OpenAPI schema and validate structure
4. Calculate SHA256 hash and compare with `.schema.hash`
5. Call `openapi-ts-client` library only if schema changed
6. Start Django development server
```

**Step 2: Update Configuration Validation section**

Replace:
- `NINJA_TS_CMD_ARGS` with `NINJA_TS_FORMAT`

```markdown
**Configuration Validation (`apps.py`):**
Django system checks validate all settings at startup:
- `NINJA_TS_API` - path to NinjaAPI instance (e.g., `"myapp.api.api"`)
- `NINJA_TS_OUTPUT_DIR` - output directory for generated client
- `NINJA_TS_DEBOUNCE_SECONDS` - delay before generation (default: 1.0)
- `NINJA_TS_FORMAT` - client format: fetch, axios, or angular (default: fetch)
```

**Step 3: Remove External Requirements section**

Delete the entire "External Requirements" section that mentions Node.js and Java.

**Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for v2.0"
```

---

## Task 8: Final Verification

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

**Step 2: Run linter**

Run: `ruff check .`
Expected: No errors

**Step 3: Run formatter check**

Run: `ruff format --check .`
Expected: No formatting issues

**Step 4: Verify package installs cleanly**

Run: `pip3 install -e .`
Expected: Success

**Step 5: Test import**

Run: `python3 -c "from django_ninja_ts.management.commands.runserver import Command; print('OK')"`
Expected: `OK`

---

## Summary

After completing all tasks:

**Removed:**
- Node.js and Java dependencies
- `_check_dependencies()` method
- `_get_platform()` method
- Subprocess-based generation
- `NINJA_TS_CMD_ARGS` setting
- Temp file handling
- Timeout handling

**Added:**
- `openapi-ts-client` dependency
- `NINJA_TS_FORMAT` setting (fetch/axios/angular)
- Direct Python API for generation

**Updated:**
- Version bumped to 2.0.0
- README with migration guide
- CLAUDE.md with updated architecture
- All tests updated for new implementation
