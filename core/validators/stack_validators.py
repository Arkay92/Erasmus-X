import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Protocol, Tuple


class StackValidator(Protocol):
    name: str

    def applies_to(self, filename: str, code: str, context: Dict | None = None) -> bool:
        ...

    def validate(self, filename: str, code: str, context: Dict | None = None) -> Tuple[bool, str]:
        ...


@dataclass
class NextJSAppRouterValidator:
    name: str = "nextjs-app-router"

    def applies_to(self, filename: str, code: str, context: Dict | None = None) -> bool:
        normalized = filename.replace("\\", "/")
        stack = (context or {}).get("stack", "")
        return "nextjs" in stack or normalized.startswith("app/") or normalized.startswith("components/")

    def validate(self, filename: str, code: str, context: Dict | None = None) -> Tuple[bool, str]:
        normalized = filename.replace("\\", "/")
        is_root_layout = normalized.endswith("layout.tsx") or normalized.endswith("layout.js")
        is_page = normalized.endswith("page.tsx") or normalized.endswith("page.js")
        is_route = normalized.endswith("route.ts") or normalized.endswith("route.js")

        if is_route:
            valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
            invalid_named_handler = re.search(r"export\s+async\s+function\s+([A-Z]+)\s+(\w+)", code)
            if invalid_named_handler:
                return False, f"Next.js Route Error: named function '{invalid_named_handler.group(2)}' after HTTP method."
            for method in re.findall(r"export\s+async\s+function\s+([a-zA-Z0-9_]+)", code):
                if method not in valid_methods and method not in {"config", "generateStaticParams"}:
                    return False, f"Next.js Route Error: invalid export '{method}' in route file."
            if "RequestHTML" in code:
                return False, "Semantic Error: invalid type 'RequestHTML'. Use Request or NextRequest."

        if is_root_layout:
            if "<html>" not in code or "<body>" not in code:
                return False, "Next.js Contract Error: root layout must contain <html> and <body>."
            if "{children}" not in code and "${children}" not in code:
                return False, "Next.js Contract Error: root layout must render children."

        if (is_root_layout or is_page) and "export default " not in code:
            return False, "Next.js Contract Error: pages and layouts need a default export."

        if "react-router-dom" in code:
            return False, "Next.js Semantic Error: use next/link or next/navigation instead of react-router-dom."

        return True, "Valid Next.js semantics"


@dataclass
class LocalDependencyValidator:
    name: str = "local-dependencies"

    def applies_to(self, filename: str, code: str, context: Dict | None = None) -> bool:
        return bool(context and context.get("available_files"))

    def validate(self, filename: str, code: str, context: Dict | None = None) -> Tuple[bool, str]:
        available_files = (context or {}).get("available_files", [])
        valid_bases = {os.path.basename(f).split(".")[0] for f in available_files}
        valid_bases.update({"components", "lib", "api", "app", "ui", "hooks", "utils", "src"})

        for imp in re.findall(r"import\s+.*?\s+from\s+['\"](.*?)['\"]", code):
            if imp == "next/file":
                return False, "Semantic Error: hallucinated import 'next/file'."
            if "next/dist/" in imp:
                return False, f"Semantic Error: internal Next.js import '{imp}'."
            if imp.startswith(("@/", "./", "../")):
                target_base = os.path.basename(imp).split(".")[0]
                if target_base not in valid_bases:
                    return False, f"Semantic Error: unresolved local dependency '{imp}'."
                if imp.count("../") > 3:
                    return False, f"Semantic Error: excessive relative path nesting in '{imp}'."
        return True, "Valid local dependencies"


@dataclass
class PlaceholderQualityValidator:
    name: str = "placeholder-quality"

    def applies_to(self, filename: str, code: str, context: Dict | None = None) -> bool:
        return True

    def validate(self, filename: str, code: str, context: Dict | None = None) -> Tuple[bool, str]:
        placeholder_patterns: Iterable[str] = (
            r"\[Placeholder.*?\]",
            r"// logic here",
            r"// Implement.*?here",
            r"TODO:.*?Implementation",
            r"return\s+<div.*?>.*?Placeholder.*?</div>",
            r"console\.log\(.*?[pP]laceholder.*?\)",
        )
        for pattern in placeholder_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, "Semantic Error: placeholder implementation detected."
        if "// TODO" in code or "// In a real app" in code or "TODO:" in code:
            return False, "Semantic Error: prototype shortcut detected."
        return True, "Valid implementation depth"


class StackValidatorRegistry:
    def __init__(self, validators: List[StackValidator] | None = None):
        self.validators = validators or [
            NextJSAppRouterValidator(),
            LocalDependencyValidator(),
            PlaceholderQualityValidator(),
        ]

    def register(self, validator: StackValidator) -> None:
        self.validators.append(validator)

    def validate(self, filename: str, code: str, context: Dict | None = None) -> Tuple[bool, str]:
        for validator in self.validators:
            if validator.applies_to(filename, code, context):
                ok, message = validator.validate(filename, code, context)
                if not ok:
                    return False, f"{validator.name}: {message}"
        return True, "Valid stack semantics"
