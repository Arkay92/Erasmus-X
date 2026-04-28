import json
import os
import re
import time
from typing import Any

from core import config


class ExecutionMemory:
    """Structured memory for builds, failures, fixes, and reusable architectures."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(config.RUNTIME_ROOT, "memories", "execution_memory.jsonl")

    def record(self, kind: str, request: str, stack: str, status: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "timestamp": time.time(),
            "kind": kind,
            "request": request,
            "stack": stack,
            "status": status,
            "data": data or {},
        }
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def record_build(self, request: str, stack: str, project_dir: str, files: list[str], verification_commands: list[str], status: str, failures: dict | None = None) -> dict[str, Any]:
        return self.record("build", request, stack, status, {
            "project_dir": project_dir,
            "files": files,
            "verification_commands": verification_commands,
            "failures": failures or {},
            "architecture": self._architecture(files),
        })

    def record_dependency_fix(self, request: str, stack: str, command: str, stderr_signature: str, fix_applied: str, final_command: str) -> dict[str, Any]:
        return self.record("dependency_fix", request, stack, "fixed", {
            "command": command,
            "stderr_signature": stderr_signature[:500],
            "fix_applied": fix_applied,
            "final_command": final_command,
        })

    def record_successful_project(self, project_name: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Record a successful project for future retrieval."""
        return self.record("successful_project", project_name, "", "success", metadata)

    def retrieve(self, request: str, stack: str = "", limit: int = 5) -> list[dict[str, Any]]:
        records = self.load()
        query_terms = self._terms(request + " " + stack)
        scored = []
        for record in records:
            haystack = " ".join([
                str(record.get("request", "")),
                str(record.get("stack", "")),
                json.dumps(record.get("data", {}), sort_keys=True),
            ])
            score = len(query_terms & self._terms(haystack))
            if stack and stack.lower() in str(record.get("stack", "")).lower():
                score += 2
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].get("timestamp", 0)), reverse=True)
        return [record for _score, record in scored[:limit]]

    def retrieve_successful_projects(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve a list of successful projects."""
        records = self.load()
        return [record for record in records if record.get("kind") == "successful_project"][:limit]

    def load(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        records = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _terms(self, text: str) -> set[str]:
        return {term for term in re.findall(r"[a-z0-9]+", text.lower()) if len(term) > 2}

    def _architecture(self, files: list[str]) -> dict[str, list[str]]:
        architecture: dict[str, list[str]] = {}
        for path in files:
            top = path.replace("\\", "/").split("/", 1)[0]
            architecture.setdefault(top, []).append(path)
        return architecture
