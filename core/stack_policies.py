from dataclasses import dataclass


@dataclass(frozen=True)
class StackPolicy:
    name: str
    guidance: str
    required_files: tuple[str, ...] = ()


class StackPolicyRegistry:
    """Registry for stack-specific constraints kept out of generic orchestration."""

    def __init__(self):
        self._policies = {
            "prisma": StackPolicy(
                name="prisma",
                required_files=("prisma/schema.prisma", "lib/db.ts"),
                guidance=(
                    'IF stack contains "prisma":\n'
                    "  - MUST use @prisma/client imports\n"
                    "  - MUST NOT use sqlite3, better-sqlite3, or raw queries\n"
                    "  - MUST include prisma/schema.prisma\n"
                    "  - MUST call prisma methods (create, update, delete, findMany)\n"
                    "  - Generated DB layer MUST be in lib/db.ts using Prisma ORM\n"
                ),
            ),
            "sqlite": StackPolicy(
                name="sqlite",
                guidance=(
                    'IF stack contains "sqlite":\n'
                    "  - CAN use better-sqlite3 or sqlite3 package\n"
                    "  - MUST NOT import @prisma/client\n"
                    "  - Define query() and execute() methods directly\n"
                ),
            ),
            "nextjs-app-router": StackPolicy(
                name="nextjs-app-router",
                guidance=(
                    'IF stack contains "nextjs-app-router":\n'
                    "  - MUST use app/ directory structure\n"
                    "  - MUST NOT use pages/ directory\n"
                    "  - MUST use API routes in app/api/\n"
                ),
            ),
        }

    def guidance_text(self) -> str:
        sections = "\n".join(policy.guidance for policy in self._policies.values())
        return f"[STACK FIDELITY ENFORCEMENT]\n{sections}\nViolation of selected stack policy = contract failure.\n"

    def apply_required_files(self, contract: dict) -> dict:
        stack = contract.get("stack", "").lower()
        critical_files = list(contract.get("critical_files", []))
        for key, policy in self._policies.items():
            if key not in stack:
                continue
            for path in reversed(policy.required_files):
                if path not in critical_files:
                    critical_files.insert(0, path)
        contract["critical_files"] = critical_files
        return contract
