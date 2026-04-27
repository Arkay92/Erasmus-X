import json
import os
import re
from typing import Any


class TrainingDataBuilder:
    def __init__(self, output_dir: str = "training_data"):
        self.output_dir = output_dir
        self.examples: list[dict[str, Any]] = []

    def collect_successful_generation(self, prompt: str, contract: dict[str, Any], generated_files: dict[str, str]) -> dict[str, Any]:
        example = {
            "type": "successful_generation",
            "prompt": prompt,
            "contract": contract,
            "generated_files": generated_files,
            "framework": self.detect_framework(prompt, contract),
        }
        self.examples.append(example)
        return example

    def collect_user_feedback(self, job_id: str, rating: int, corrections: dict[str, str]) -> dict[str, Any]:
        example = {
            "type": "user_feedback",
            "job_id": job_id,
            "rating": rating,
            "corrections": corrections,
        }
        self.examples.append(example)
        return example

    def export_for_training(self, framework: str = "generic") -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, f"{framework}_projects.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for example in self.examples:
                if framework == "generic" or example.get("framework") == framework:
                    fh.write(json.dumps(example, sort_keys=True) + "\n")
        return path

    def generate_prompt_from_code(self, filename: str, code: str) -> str:
        symbols = re.findall(r"(?:class|def|function|const|export function)\s+([A-Za-z_][\w]*)", code)
        summary = ", ".join(symbols[:8]) if symbols else "the provided implementation"
        return f"Implement {filename} containing {summary}."

    def detect_framework(self, prompt: str, contract: dict[str, Any] | None = None) -> str:
        text = (prompt + " " + json.dumps(contract or {})).lower()
        if "next.js" in text or "nextjs" in text or "tsx" in text:
            return "nextjs"
        if "fastapi" in text:
            return "fastapi"
        if "rust" in text or "cargo" in text:
            return "rust"
        return "generic"
