import json
import os
import re
import time
from typing import Any

from core import config
from core.scaffold_registry import Scaffold


class AutoPackBuilder:
    """Promotes verified successful project scaffolds into reusable feature packs."""

    def __init__(self, brain=None, marketplace_path: str | None = None):
        self.brain = brain
        self.marketplace_path = marketplace_path or os.path.join(config.RUNTIME_ROOT, "memories", "pack_marketplace.jsonl")

    def maybe_create_pack(self, request: str, scaffold: Scaffold, saved_files: list[str], failures: dict | None = None) -> dict[str, Any] | None:
        if failures or not saved_files:
            return None
        if not self._has_tests(saved_files) or not scaffold.verification_commands:
            return None

        pack_name = self._pack_name(request, scaffold)
        files = [{"path": path, "content": scaffold.files[path]} for path in saved_files if path in scaffold.files]
        pack = {
            "feature": pack_name,
            "source": "auto_pack_builder",
            "stack": scaffold.stack,
            "request": request,
            "created_at": time.time(),
            "triggers": self._triggers(request, scaffold),
            "verification_commands": scaffold.verification_commands,
            "critical_files": saved_files,
            "files": files,
        }
        if self.brain:
            self.brain.register_feature_pack(pack_name, pack)
        self._append_marketplace(pack)
        return pack

    def _pack_name(self, request: str, scaffold: Scaffold) -> str:
        lower = request.lower()
        if "crm" in lower:
            base = "crm_pack"
        elif "booking" in lower:
            base = "booking_business_pack"
        elif "plumber" in lower:
            base = "plumber_booking_pack"
        else:
            terms = re.findall(r"[a-z0-9]+", lower)[:4]
            base = "_".join(terms or [scaffold.name]) + "_pack"
        return re.sub(r"[^a-z0-9_]", "_", base)

    def _triggers(self, request: str, scaffold: Scaffold) -> list[str]:
        triggers = {request.lower(), scaffold.name, scaffold.stack}
        for token in re.findall(r"[a-z0-9]+", request.lower()):
            if len(token) > 3:
                triggers.add(token)
        return sorted(triggers)

    def _has_tests(self, files: list[str]) -> bool:
        return any(
            path.replace("\\", "/").startswith(("test/", "tests/"))
            or path.endswith((".test.ts", ".test.tsx", "_test.py", "_test.c", "Test.php"))
            for path in files
        )

    def _append_marketplace(self, pack: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.marketplace_path), exist_ok=True)
        with open(self.marketplace_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(pack, sort_keys=True) + "\n")
