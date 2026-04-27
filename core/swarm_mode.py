class SwarmMode:
    """Deterministic shard planning for complex product builds."""

    ROLES = ("architect", "builder", "tester", "critic", "security")

    def should_activate(self, request: str) -> bool:
        lower = request.lower()
        return any(term in lower for term in ("saas", "business", "booking", "crm", "marketplace", "payments"))

    def plan(self, request: str) -> dict:
        return {
            "request": request,
            "roles": {
                "architect": "Define app routes, data model, and integration boundaries.",
                "builder": "Generate production files from the manifest and selected scaffold packs.",
                "tester": "Require unit tests, route tests, and verification commands.",
                "critic": "Reject placeholders, missing imports, schema drift, and hollow flows.",
                "security": "Check auth, password hashing, session cookies, validation, and secret defaults.",
            },
            "merge_policy": "Only merge files that pass validators and satisfy the manifest.",
        }

    def as_markdown(self, request: str) -> str:
        plan = self.plan(request)
        lines = ["# Swarm Plan", "", f"Request: {request}", "", "## Shards"]
        for role in self.ROLES:
            lines.append(f"- {role}: {plan['roles'][role]}")
        lines.extend(["", f"Merge policy: {plan['merge_policy']}", ""])
        return "\n".join(lines)
