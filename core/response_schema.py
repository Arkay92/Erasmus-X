from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List


@dataclass
class AgentResponse:
    """Structured response returned by public agent entry points.

    Iteration preserves the legacy `(raw, clean)` unpacking contract.
    """

    answer: str
    files: List[str] = field(default_factory=list)
    status: str = "ok"
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""

    def __post_init__(self) -> None:
        if not self.raw:
            self.raw = self.answer

    def __iter__(self) -> Iterator[str]:
        yield self.raw
        yield self.answer

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def make_response(raw: str, answer: str = "", **kwargs: Any) -> AgentResponse:
    return AgentResponse(answer=answer or raw or "", raw=raw or "", **kwargs)
