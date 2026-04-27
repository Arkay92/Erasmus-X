from typing import Any
from core.import_resolver import find_relative_imports, relative_import_candidates


class GraphReasoner:
    def __init__(self, kg: Any):
        self.kg = kg

    def plan_project(self, request: str) -> list[str]:
        facts = self.kg.get_related_facts(request) if self.kg else []
        reusable = self.extract_patterns(facts)
        planned = self.topological_sort(reusable)
        return planned or ["plan", "scaffold", "implement", "validate"]

    def extract_patterns(self, facts: list[str]) -> list[str]:
        patterns = []
        for fact in facts:
            if "depends" in fact or "imports" in fact or "requires" in fact:
                patterns.append(fact)
        return patterns

    def topological_sort(self, patterns: list[str]) -> list[str]:
        # Lightweight placeholder until KG stores typed dependency nodes.
        return sorted(dict.fromkeys(patterns))

    def detect_conflicts(self, contract: dict[str, Any], implementations: dict[str, str]) -> list[dict[str, str]]:
        conflicts = []
        available = set(implementations.keys())
        for filename, content in implementations.items():
            for target in find_relative_imports(content):
                if not self._resolve_relative(filename, target, available):
                    conflicts.append({"file": filename, "reason": f"Unresolved relative import: {target}"})
        for critical in contract.get("critical_files", []):
            if critical not in available:
                conflicts.append({"file": critical, "reason": "Critical contract file is missing"})
        return conflicts

    def _resolve_relative(self, source: str, target: str, available: set[str]) -> bool:
        return bool(relative_import_candidates(source, target) & available)
