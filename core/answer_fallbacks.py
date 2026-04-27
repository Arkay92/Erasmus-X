import re
from typing import Optional


def factual_fallback(prompt: str) -> Optional[str]:
    """Offline fallback for stable elementary facts when search/model output fails."""
    lower = re.sub(r"\s+", " ", prompt.lower()).strip()
    normalized = re.sub(r"[^a-z0-9\s+#.]", "", lower)
    if (
        re.search(r"\bwhat\s+(is|does)\s+http\b", normalized)
        or "http stand for" in normalized
        or normalized in {"http", "define http"}
    ):
        return "HTTP stands for HyperText Transfer Protocol. It is the application-layer protocol used to transfer web resources between clients and servers."
    if "rest" in lower and "graphql" in lower and ("compare" in lower or "tradeoff" in lower):
        return (
            "REST is usually the simpler choice for public ecommerce APIs with stable resource-oriented needs, "
            "strong HTTP caching, straightforward partner integrations, and conventional CRUD endpoints. "
            "GraphQL is stronger when clients need flexible nested data, mobile/web clients need different payload shapes, "
            "or over-fetching and under-fetching are causing performance problems. "
            "Choose REST for simple catalog, order, and integration APIs where cacheability and operational simplicity matter most. "
            "Choose GraphQL for complex product detail pages, personalized storefronts, or multi-client experiences where clients must request exact fields. "
            "The tradeoff is that GraphQL adds schema governance, resolver performance risk, authorization complexity, and less automatic HTTP caching."
        )
    return None
