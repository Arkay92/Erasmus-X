import ast
import os
import re
from typing import Any


class ActiveKGBuilder:
    def __init__(self, kg: Any):
        self.kg = kg

    def extract_from_project(self, generated_files: dict[str, str]) -> None:
        for filename, content in generated_files.items():
            self._add_entity(filename, "file", os.path.splitext(filename)[1].lstrip(".") or "unknown")
            for dep in self._extract_imports(filename, content):
                self._add_relation(filename, "imports", dep)
            for symbol in self._extract_symbols(filename, content):
                self._add_relation(filename, "defines", symbol)

    def _add_entity(self, subject: str, relation: str, obj: str) -> None:
        if self.kg:
            self.kg.add_triplet(subject, relation, obj)

    def _add_relation(self, subject: str, relation: str, obj: str) -> None:
        if self.kg and obj:
            self.kg.add_triplet(subject, relation, obj)

    def _extract_imports(self, filename: str, content: str) -> list[str]:
        if filename.endswith(".py"):
            try:
                tree = ast.parse(content)
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.append(node.module)
                return imports
            except SyntaxError:
                return []
        imports = re.findall(r"from ['\"]([^'\"]+)['\"]|import\(['\"]([^'\"]+)['\"]\)", content)
        return [part for match in imports for part in match if part]

    def _extract_symbols(self, filename: str, content: str) -> list[str]:
        if filename.endswith(".py"):
            try:
                tree = ast.parse(content)
                return [node.name for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
            except SyntaxError:
                return []
        return re.findall(r"(?:class|function|const|let|var|interface|type)\s+([A-Za-z_][\w]*)", content)
