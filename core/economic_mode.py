import re


class EconomicMode:
    """Small decision layer for reuse, template value, and business potential."""

    BUSINESS_TERMS = {
        "booking", "crm", "saas", "business", "payments", "stripe", "admin",
        "dashboard", "customers", "invoices", "appointments", "plumber",
    }

    def evaluate(self, request: str, available_packs: list[str] | None = None) -> dict:
        lower = request.lower()
        terms = set(re.findall(r"[a-z0-9]+", lower))
        matching_packs = [pack for pack in available_packs or [] if any(term in pack for term in terms)]
        business_score = len(terms & self.BUSINESS_TERMS)
        return {
            "use_existing_pack": bool(matching_packs),
            "matching_packs": matching_packs[:5],
            "should_template": business_score >= 2 or any(term in lower for term in ("build me", "business", "saas")),
            "sellable_output": business_score >= 3,
            "recommended_defaults": self._defaults(terms),
        }

    def _defaults(self, terms: set[str]) -> list[str]:
        defaults = []
        if terms & {"booking", "appointments", "plumber"}:
            defaults.extend(["bookings", "admin dashboard", "customer notifications"])
        if terms & {"saas", "business", "crm"}:
            defaults.extend(["auth", "database", "tests", "deploy script"])
        if terms & {"payments", "stripe", "invoices"}:
            defaults.append("payments")
        return sorted(set(defaults))

    def suggest_profitable_niche(self, location: str, industry: str) -> str:
        """Suggest a profitable niche based on location and industry."""
        return f"Based on our analysis, a {industry} platform in {location} with booking and payment features could be highly profitable."
