import ast
import os
import re
import subprocess
from typing import Iterable


class CodeFormatter:
    """Best-effort formatter that avoids mandatory external dependencies."""

    def format(self, filename: str, code: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".py":
            return self._format_python(code)
        if ext in {".js", ".jsx", ".ts", ".tsx", ".css", ".json"}:
            return self._format_with_prettier(filename, code)
        if ext == ".go":
            return self._format_with_command(["gofmt"], code)
        return code

    def _format_python(self, code: str) -> str:
        code = self._organize_python_imports(code)
        formatted = self._format_with_command(["black", "-q", "-"], code)
        return formatted if formatted != code else code.rstrip() + "\n"

    def _organize_python_imports(self, code: str) -> str:
        lines = code.splitlines()
        imports: list[str] = []
        body_start = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(line)
                body_start = idx + 1
                continue
            break
        if not imports:
            return code
        body = "\n".join(lines[body_start:]).lstrip("\n")
        grouped = sorted(dict.fromkeys(imports), key=lambda item: (self._import_group(item), item.lower()))
        return "\n".join(grouped) + "\n\n" + body

    def _import_group(self, line: str) -> int:
        third_party_markers = ("from django", "from fastapi", "from pydantic", "import numpy", "import pandas")
        local_markers = ("from .", "from core", "from utils", "import core", "import utils")
        stripped = line.strip()
        if stripped.startswith(local_markers):
            return 2
        if stripped.startswith(third_party_markers):
            return 1
        return 0

    def _format_with_prettier(self, filename: str, code: str) -> str:
        parser = {
            ".js": "babel",
            ".jsx": "babel",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".css": "css",
            ".json": "json",
        }.get(os.path.splitext(filename)[1].lower(), "babel")
        return self._format_with_command(["npx", "prettier", "--parser", parser], code)

    def _format_with_command(self, command: Iterable[str], code: str) -> str:
        try:
            proc = subprocess.run(list(command), input=code, text=True, capture_output=True, timeout=10)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout
        except Exception:
            pass
        return code.rstrip() + "\n"
