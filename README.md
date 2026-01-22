# Django Ninja TS Generator

Automatically builds your TypeScript client whenever your Django Ninja schema changes.

## Installation

1. Install the package:

   ```bash
   pip install django-ninja-ts
   ```

2. Add to `INSTALLED_APPS` in `settings.py`:

   ```python
   INSTALLED_APPS = [
       # ...
       'django.contrib.staticfiles',
       'django_ninja_ts',  # Add this
       # ...
   ]
   ```

## Requirements

This package requires the following external dependencies:

- **Node.js** (for `npx`)
- **Java JRE** (for OpenAPI Generator)

The package will provide installation instructions if these are missing.

## Configuration

Add these settings to your `settings.py`:

```python
import os

# Path to your NinjaAPI instance (dot notation)
NINJA_TS_API = 'myproject.api.api'

# Where to output the generated client
NINJA_TS_OUTPUT_DIR = os.path.join(BASE_DIR, '../frontend/src/app/shared/api')

# Optional: Debounce time in seconds (prevents rapid rebuilds on "Save All")
# Default: 1.0
NINJA_TS_DEBOUNCE_SECONDS = 0.5

# Optional: Override generator arguments
# Default: ['generate', '-g', 'typescript-angular', '-p', 'removeOperationIdPrefix=true']
# NINJA_TS_CMD_ARGS = ['generate', '-g', 'typescript-axios']
```

## How It Works

1. When you run `python manage.py runserver`, the package intercepts the command
2. It loads your Django Ninja API and extracts the OpenAPI schema
3. It calculates a hash of the schema and compares it to the previous build
4. If the schema has changed, it runs `openapi-generator-cli` via `npx` to generate the TypeScript client
5. The hash is stored in `.schema.hash` in the output directory to avoid unnecessary rebuilds

## Configuration Options

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `NINJA_TS_API` | Yes | - | Dot-notation path to your NinjaAPI instance |
| `NINJA_TS_OUTPUT_DIR` | Yes | - | Directory where the TypeScript client will be generated |
| `NINJA_TS_DEBOUNCE_SECONDS` | No | `1.0` | Delay before generation to handle rapid file saves |
| `NINJA_TS_CMD_ARGS` | No | See below | Arguments passed to openapi-generator-cli |

### Default Generator Arguments

```python
['generate', '-g', 'typescript-angular', '-p', 'removeOperationIdPrefix=true']
```

### Example: Using Axios Instead of Angular

```python
NINJA_TS_CMD_ARGS = ['generate', '-g', 'typescript-axios']
```

### Example: Using Fetch API

```python
NINJA_TS_CMD_ARGS = ['generate', '-g', 'typescript-fetch']
```

## License

MIT License - see [LICENSE](LICENSE) for details.
