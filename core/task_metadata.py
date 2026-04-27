from dataclasses import asdict, dataclass
from typing import Optional

from core import config


@dataclass(frozen=True)
class TaskMetadata:
    intent: str
    confidence: float
    mode: str
    is_code: bool = False
    is_project: bool = False
    is_dynamic: bool = False
    target_stack: str = "generic"
    language: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


def is_dynamic_query(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in getattr(config, "DYNAMIC_ONLY_KEYWORDS", []))
