"""Custom runserver command that generates TypeScript clients from Django Ninja schemas."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from typing import Any

from django.conf import settings
from django.core.management.commands.runserver import Command as RunserverCommand
from django.utils.module_loading import import_string


class Command(RunserverCommand):
    """Extended runserver command that auto-generates TypeScript clients."""

    def inner_run(self, *args: Any, **options: Any) -> None:
        """Run the server with TypeScript client generation."""
        # 1. Debounce (Wait for rapid file saves to settle)
        self._debounce()

        # 2. Check dependencies and run generation
        if self._check_dependencies():
            self._generate_client()

        # 3. Start the actual Django server
        super().inner_run(*args, **options)

    def _debounce(self) -> None:
        """
        Sleep briefly to let the auto-reloader kill this process.

        This handles the case where a subsequent file change occurs
        immediately (e.g. 'Save All').
        """
        delay: float = getattr(settings, "NINJA_TS_DEBOUNCE_SECONDS", 1.0)
        if delay > 0:
            time.sleep(delay)

    def _check_dependencies(self) -> bool:
        """Verify that npx and java are available."""
        missing: list[str] = []
        if not shutil.which("npx"):
            missing.append("node")
        if not shutil.which("java"):
            missing.append("java")

        if not missing:
            return True

        self.stdout.write(
            self.style.ERROR(
                "TypeScript Client Generation Failed: Missing Dependencies"
            )
        )

        os_name = platform.system().lower()

        if "node" in missing:
            self.stdout.write(self.style.WARNING("  [Node.js missing]"))
            if "darwin" in os_name:
                self.stdout.write("    Run: brew install node")
            elif "linux" in os_name:
                self.stdout.write("    Run: sudo apt install nodejs npm")
            elif "windows" in os_name:
                self.stdout.write("    Download: https://nodejs.org/")

        if "java" in missing:
            self.stdout.write(self.style.WARNING("  [Java JRE missing]"))
            if "darwin" in os_name:
                self.stdout.write("    Run: brew install openjdk")
            elif "linux" in os_name:
                self.stdout.write("    Run: sudo apt install default-jre")
            elif "windows" in os_name:
                self.stdout.write("    Download: https://www.java.com/download/")

        self.stdout.write("-" * 30)
        return False

    def _generate_client(self) -> None:
        """Generate the TypeScript client if the schema has changed."""
        api_path: str | None = getattr(settings, "NINJA_TS_API", None)
        output_dir: str | None = getattr(settings, "NINJA_TS_OUTPUT_DIR", None)

        if not api_path or not output_dir:
            return

        try:
            # Resolve paths
            output_dir = os.path.abspath(output_dir)
            hash_file = os.path.join(output_dir, ".schema.hash")

            # Load API
            api = import_string(api_path)
            schema_dict: dict[str, Any] = api.get_openapi_schema()

            # Calculate Hash
            schema_str = json.dumps(schema_dict, sort_keys=True).encode("utf-8")
            new_hash = hashlib.md5(schema_str).hexdigest()

            # Compare Hash
            if self._is_schema_changed(new_hash, hash_file):
                self._run_generator(schema_dict, output_dir, hash_file, new_hash)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Generation Error: {e}"))

    def _is_schema_changed(self, new_hash: str, hash_file: str) -> bool:
        """Check if the schema has changed since last generation."""
        if not os.path.exists(hash_file):
            return True
        try:
            with open(hash_file, "r") as f:
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
        """Run the OpenAPI generator to create the TypeScript client."""
        tmp_path: str | None = None

        try:
            # Write schema to temp file
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".json", delete=False
            ) as tmp:
                json.dump(schema_dict, tmp)
                tmp_path = tmp.name

            cmd_args: list[str] = getattr(
                settings,
                "NINJA_TS_CMD_ARGS",
                [
                    "generate",
                    "-g",
                    "typescript-fetch",
                ],
            )

            # Windows needs shell=True for npx if it's a batch file
            use_shell = os.name == "nt"
            cmd = (
                ["npx", "openapi-generator-cli"]
                + cmd_args
                + ["-o", output_dir, "-i", tmp_path]
            )

            self.stdout.write(f"Generating Client to {output_dir}...")
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=use_shell,
            )

            # Save new hash
            os.makedirs(output_dir, exist_ok=True)
            with open(hash_file, "w") as f:
                f.write(new_hash)

            self.stdout.write(self.style.SUCCESS("Client generation successful."))

        except subprocess.CalledProcessError:
            self.stdout.write(
                self.style.ERROR(
                    "Client generation failed. Check console for details."
                )
            )

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
