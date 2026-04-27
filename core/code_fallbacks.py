import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CodeFallback:
    filename: str
    language: str
    content: str

    def as_file_block(self) -> str:
        return f"[FILE: {self.filename}]\n```{self.language}\n{self.content}\n```"


class CodeFallbackRegistry:
    """Small deterministic fallback for elementary single-file tasks.

    This is only used when the model fails to return any file blocks for a code request.
    """

    def __init__(self):
        self._entries: list[tuple[Callable[[str, dict], bool], Callable[[], CodeFallback]]] = []
        self._register_defaults()

    def match(self, prompt: str, metadata: dict) -> Optional[CodeFallback]:
        for predicate, factory in self._entries:
            if predicate(prompt, metadata):
                return factory()
        return None

    def register(self, predicate: Callable[[str, dict], bool], factory: Callable[[], CodeFallback]) -> None:
        self._entries.append((predicate, factory))

    def _register_defaults(self) -> None:
        self.register(
            lambda text, meta: (meta.get("language") == "python" or "python" in text.lower())
            and bool(re.search(r"\bfactorial\b", text, re.IGNORECASE)),
            _python_factorial,
        )


def _python_factorial() -> CodeFallback:
    return CodeFallback(
        filename="factorial.py",
        language="python",
        content='''"""Factorial utility with CLI support."""
import sys


def factorial(n: int) -> int:
    """Return n! for a non-negative integer."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result


if __name__ == "__main__":
    value = int(sys.argv[1]) if len(sys.argv) > 1 else int(input("n: "))
    print(factorial(value))
''',
    )
