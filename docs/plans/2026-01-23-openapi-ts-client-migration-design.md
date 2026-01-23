# Migration to openapi-ts-client

## Overview

Replace `openapi-generator-cli` (requires Node.js + Java) with `openapi-ts-client` (pure Python) for TypeScript client generation.

## Configuration

### Removed Settings
- `NINJA_TS_CMD_ARGS` - no longer applicable

### New Settings
- `NINJA_TS_FORMAT` - client format: `"fetch"` (default), `"axios"`, or `"angular"`

### Example Configuration
```python
NINJA_TS_API = "myproject.api.api"
NINJA_TS_OUTPUT_DIR = os.path.join(BASE_DIR, "../frontend/src/api")
NINJA_TS_FORMAT = "fetch"  # Optional, defaults to "fetch"
# NINJA_TS_DEBOUNCE_SECONDS = 0.5  # Optional, defaults to 1.0
```

## Implementation

### runserver.py Changes

**Remove:**
- `_check_dependencies()` method
- `_get_platform()` method
- Subprocess handling, temp file management, timeout logic

**Update `_run_generator()`:**
```python
from openapi_ts_client import generate_typescript_client, ClientFormat

FORMAT_MAP = {
    "fetch": ClientFormat.FETCH,
    "axios": ClientFormat.AXIOS,
    "angular": ClientFormat.ANGULAR,
}

def _run_generator(self, schema_dict, output_dir, hash_file, new_hash):
    format_name = getattr(settings, "NINJA_TS_FORMAT", "fetch")
    client_format = FORMAT_MAP[format_name]

    self.stdout.write(f"Generating {format_name} client to {output_dir}...")

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
```

**Error handling:**
- Catch `ValueError` (invalid spec) and `TypeError` (wrong spec type)
- Remove `subprocess.CalledProcessError`, `subprocess.TimeoutExpired` handling

### apps.py Changes

- Remove validation for `NINJA_TS_CMD_ARGS`
- Add validation for `NINJA_TS_FORMAT` - must be one of `fetch`, `axios`, `angular`

### pyproject.toml Changes

- Version: `1.0.0` → `2.0.0`
- Add dependency: `openapi-ts-client>=1.0.0`

## Documentation

### README Updates

**Requirements:**
- Remove Node.js and Java requirements

**Configuration:**
- Remove `NINJA_TS_CMD_ARGS` documentation
- Add `NINJA_TS_FORMAT` documentation

**Troubleshooting - Remove:**
- Node.js/Java missing errors
- Generation timeout issues
- Windows npx issues

**Add migration note:**
```markdown
## Migrating from v1.x

v2.0 switched from `openapi-generator-cli` (Node.js/Java) to `openapi-ts-client` (pure Python).

- Remove `NINJA_TS_CMD_ARGS` from settings
- Add `NINJA_TS_FORMAT` if you need axios or angular (fetch is default)
- Node.js and Java are no longer required
```

### CLAUDE.md Updates

- Remove Node.js and Java from external requirements
- Update generation flow description
- Update configuration list

## Tests

**Remove tests for:**
- `_check_dependencies()` method
- `_get_platform()` method
- Node.js/Java missing scenarios
- Subprocess timeout handling
- `NINJA_TS_CMD_ARGS` validation

**Update tests for:**
- `_run_generator()` - mock `generate_typescript_client` instead of `subprocess.run`
- System checks - validate `NINJA_TS_FORMAT`

**Add tests for:**
- `NINJA_TS_FORMAT` validation (valid values)
- `NINJA_TS_FORMAT` invalid value error
- Default format when not set

## Files to Modify

1. `django_ninja_ts/management/commands/runserver.py`
2. `django_ninja_ts/apps.py`
3. `pyproject.toml`
4. `README.md`
5. `CLAUDE.md`
6. `tests/test_runserver.py`

## Benefits

- No external runtime dependencies (Node.js, Java)
- Simpler configuration
- Faster generation (no subprocess overhead)
- Easier installation for users
