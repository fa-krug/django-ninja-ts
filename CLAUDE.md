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
    └── runserver.py     # Custom runserver: debounce → check deps → generate → start server
```

**Generation Flow (`runserver.py`):**
1. Debounce rapid file saves (configurable delay)
2. Check for Node.js and Java dependencies
3. Load NinjaAPI from configured Django settings path
4. Get OpenAPI schema and validate structure
5. Calculate SHA256 hash and compare with `.schema.hash`
6. Run `npx openapi-generator-cli` only if schema changed
7. Start Django development server

**Configuration Validation (`apps.py`):**
Django system checks validate all settings at startup:
- `NINJA_TS_API` - path to NinjaAPI instance (e.g., `"myapp.api.api"`)
- `NINJA_TS_OUTPUT_DIR` - output directory for generated client
- `NINJA_TS_DEBOUNCE_SECONDS` - delay before generation (default: 0)
- `NINJA_TS_CMD_ARGS` - custom OpenAPI generator arguments

## Code Style

- Python 3.8+ with full type annotations (PEP 561 marker included)
- Ruff for linting (rules: E, W, F, I, B, C4, UP, DJ) and formatting
- Line length: 88 characters
- Double quotes for strings

## External Requirements

- Node.js (for npx command)
- Java JRE (for OpenAPI Generator)
