import re
from typing import Any


class ModelRouter:
    """Routes requests to framework-specialized models when configured."""

    FRAMEWORK_PATTERNS = {
        "nextjs": [r"next\.js", r"nextjs", r"app router", r"tsx"],
        "fastapi": [r"fastapi", r"pydantic", r"uvicorn"],
        "rust": [r"\brust\b", r"cargo", r"actix", r"axum"],
        "go": [r"\bgolang\b", r"\bgo\b", r"gin gonic"],
    }

    def __init__(self, default_model: str, specialized_models: dict[str, str] | None = None):
        self.default_model = default_model
        self.specialized_models = specialized_models or {}

    def detect_framework(self, request: Any) -> str:
        text = str(request).lower()
        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return framework
        return "generic"

    def route(self, request: Any) -> str:
        framework = self.detect_framework(request)
        return self.specialized_models.get(framework, self.default_model)
