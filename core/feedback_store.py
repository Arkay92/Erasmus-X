import json
import os
import time
from typing import Any

from core import config


class FeedbackStore:
    def __init__(self, path: str | None = None):
        if path is None:
            path = os.path.join(config.RUNTIME_ROOT, "memories", "feedback.jsonl")
        self.path = path

    def submit(self, job_id: str, rating: int, corrections: dict[str, str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if rating < 1 or rating > 5:
            raise ValueError("rating must be between 1 and 5")
        feedback = {
            "job_id": job_id,
            "rating": rating,
            "corrections": corrections or {},
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(feedback, sort_keys=True) + "\n")
        return feedback

    def load(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        records = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
