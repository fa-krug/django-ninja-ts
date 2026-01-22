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

## Logging

The package uses Python's standard logging module. To see debug output, configure logging in your settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_ninja_ts': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Troubleshooting

### Common Issues

#### "Module not found" error

**Problem:** You see an error like `Generation Error: Module not found: No module named 'myapp'`

**Solution:** Ensure `NINJA_TS_API` contains a valid import path to your NinjaAPI instance:
```python
# Correct - full import path
NINJA_TS_API = 'myapp.api.api'

# Incorrect - missing module path
NINJA_TS_API = 'api'
```

#### "does not have 'get_openapi_schema' method" error

**Problem:** The object at your `NINJA_TS_API` path is not a NinjaAPI instance.

**Solution:** Ensure you're pointing to the actual NinjaAPI instance, not a module or router:
```python
# In myapp/api.py
from ninja import NinjaAPI
api = NinjaAPI()  # This is what NINJA_TS_API should point to

# In settings.py
NINJA_TS_API = 'myapp.api.api'  # Points to the 'api' variable in myapp/api.py
```

#### "Invalid OpenAPI schema" error

**Problem:** The schema returned by your API is missing required OpenAPI fields.

**Solution:** This usually indicates a configuration issue with your NinjaAPI. Ensure your API has:
- A title (set in NinjaAPI constructor or via `title` parameter)
- At least one endpoint registered

```python
api = NinjaAPI(title="My API", version="1.0.0")

@api.get("/health")
def health(request):
    return {"status": "ok"}
```

#### Generation hangs indefinitely

**Problem:** The TypeScript generation process never completes.

**Solution:** The package has a 120-second timeout by default. If generation regularly times out:
1. Check that Java and Node.js are properly installed
2. Try running `npx openapi-generator-cli generate --help` manually
3. Check for network issues (first run downloads the generator)

#### "Output directory parent is not writable" error

**Problem:** The package cannot create files in the specified output directory.

**Solution:** Ensure the parent directory of `NINJA_TS_OUTPUT_DIR` exists and has write permissions:
```bash
# Check permissions
ls -la /path/to/parent/directory

# Fix permissions if needed
chmod 755 /path/to/parent/directory
```

#### Schema not regenerating after changes

**Problem:** You've made API changes but the TypeScript client isn't updating.

**Solution:**
1. Delete the `.schema.hash` file in your output directory
2. Restart the development server
3. If using `NINJA_TS_DEBOUNCE_SECONDS`, wait for the debounce period

#### Windows-specific issues

**Problem:** Commands fail on Windows with shell-related errors.

**Solution:** The package automatically uses `shell=True` on Windows for `npx` compatibility. If you still have issues:
1. Ensure Node.js is in your PATH
2. Try running from PowerShell instead of Command Prompt
3. Run `npx openapi-generator-cli` manually to verify setup

### Configuration Validation

The package validates your configuration at startup using Django's system checks. Run checks manually with:

```bash
python manage.py check
```

This will report any configuration errors like:
- Missing required settings
- Invalid setting types
- Unwritable output directories

### Debug Mode

Enable debug logging to see detailed information about the generation process:

```python
LOGGING = {
    'version': 1,
    'loggers': {
        'django_ninja_ts': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Supported OpenAPI Generator Versions

This package works with any version of `@openapitools/openapi-generator-cli` available via npm. The generator is automatically downloaded on first use.

## License

MIT License - see [LICENSE](LICENSE) for details.
