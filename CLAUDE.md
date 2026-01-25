# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django Ninja TypeScript Generator - automatically generates TypeScript/JavaScript API clients whenever Django Ninja's OpenAPI schema changes. Intercepts Django's `runserver` command to generate typed clients using OpenAPI Generator.

## Commands

```bash
# Run tests
pytest

# Run a single test
pytest tests/test_runserver.py::TestCheckDependencies::test_method_name

# Lint check
ruff check .

# Format code
ruff format .

# Install with dev dependencies
pip install -e ".[dev]"

# Run pre-commit hooks manually
pre-commit run --all-files
```

## Architecture

The package extends Django's `runserver` command to automatically generate TypeScript clients:

```
django_ninja_ts/
├── apps.py              # Django app config with system checks for configuration validation
└── management/commands/
    ├── runserver.py         # Custom runserver: debounce → check deps → generate → start server
    └── generate_ts_client.py # Manual generation command with --force option
```

**Generation Flow (`runserver.py`):**
1. Debounce rapid file saves (configurable delay)
2. Load NinjaAPI from configured Django settings path
3. Get OpenAPI schema and validate structure
4. Calculate SHA256 hash and compare with `.schema.hash`
5. Call `openapi-ts-client` library only if schema changed
6. Start Django development server

**Configuration Validation (`apps.py`):**
Django system checks validate all settings at startup:
- `NINJA_TS_API` - path to NinjaAPI instance (e.g., `"myapp.api.api"`)
- `NINJA_TS_OUTPUT_DIR` - output directory for generated client
- `NINJA_TS_DEBOUNCE_SECONDS` - delay before generation (default: 1.0)
- `NINJA_TS_FORMAT` - client format: fetch, axios, or angular (default: fetch)
- `NINJA_TS_CLEAN` - clear output directory before generation (default: True)
- `NINJA_TS_AUTO_GENERATE` - enable auto-generation on runserver (default: True)

## Code Style

- Python 3.8+ with full type annotations (PEP 561 marker included)
- Ruff for linting (rules: E, W, F, I, B, C4, UP, DJ) and formatting
- Line length: 88 characters
- Double quotes for strings

## Git Conventions

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
test(apps): add system check validation tests
chore(deps): update openapi-generator-cli version
```

## Documentation Maintenance

**IMPORTANT:** After making any code changes, always update the relevant documentation:

1. **README.md** - Update user-facing documentation:
   - New settings or configuration options
   - New commands or features
   - Changes to existing behavior
   - New troubleshooting sections if needed

2. **CLAUDE.md** - Update developer/AI guidance:
   - Architecture changes
   - New files or commands
   - Updated configuration options in the settings list

