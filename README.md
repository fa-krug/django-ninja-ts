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

## Migrating from v1.x

v2.0 switched from `openapi-generator-cli` (Node.js/Java) to `openapi-ts-client` (pure Python).

**Breaking changes:**
- Remove `NINJA_TS_CMD_ARGS` from your settings (no longer supported)
- Add `NINJA_TS_FORMAT` if you need axios or angular (fetch is default)
- Node.js and Java are no longer required

## Configuration

Add these settings to your `settings.py`:

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

# Optional: Clear output directory before generation
# Default: True
# NINJA_TS_CLEAN = True
```

## How It Works

1. When you run `python manage.py runserver`, the package intercepts the command
2. It loads your Django Ninja API and extracts the OpenAPI schema
3. It calculates a hash of the schema and compares it to the previous build
4. If the schema has changed, it runs `openapi-ts-client` to generate the TypeScript client
5. The hash is stored in `.schema.hash` in the output directory to avoid unnecessary rebuilds

## Configuration Options

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `NINJA_TS_API` | Yes | - | Dot-notation path to your NinjaAPI instance |
| `NINJA_TS_OUTPUT_DIR` | Yes | - | Directory where the TypeScript client will be generated |
| `NINJA_TS_FORMAT` | No | `fetch` | Client format: `fetch`, `axios`, or `angular` |
| `NINJA_TS_DEBOUNCE_SECONDS` | No | `1.0` | Delay before generation to handle rapid file saves |
| `NINJA_TS_CLEAN` | No | `True` | Clear output directory before generation |

### Example: Using Axios

```python
NINJA_TS_FORMAT = 'axios'
```

### Example: Using Angular

```python
NINJA_TS_FORMAT = 'angular'
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

## Contributing

### Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

**Format:** `<type>(<scope>): <description>`

**Types:**
- `feat` - New features
- `fix` - Bug fixes
- `docs` - Documentation changes
- `style` - Code style changes (formatting, whitespace)
- `refactor` - Code refactoring without feature changes
- `test` - Adding or updating tests
- `chore` - Maintenance tasks, dependencies, configs

**Examples:**
```bash
feat(generator): add support for axios client
fix(runserver): handle missing Java dependency gracefully
docs(readme): add troubleshooting section
```

## License

MIT License - see [LICENSE](LICENSE) for details.
