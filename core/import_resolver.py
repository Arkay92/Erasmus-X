import re


def find_relative_imports(content: str) -> list[str]:
    """Extract relative JS/TS import specifiers from source content."""
    imports = re.findall(
        r"from ['\"](\.{1,2}/[^'\"]+)['\"]|import .* from ['\"](\.{1,2}/[^'\"]+)['\"]",
        content,
    )
    return [part for match in imports for part in match if part]


def relative_import_candidates(source: str, target: str) -> set[str]:
    """Return plausible project paths for a relative import target."""
    base = source.rsplit('/', 1)[0] if '/' in source else ''
    raw = f"{base}/{target}".replace('/./', '/').lstrip('./')
    return {
        raw,
        raw + '.ts',
        raw + '.tsx',
        raw + '.js',
        raw + '.jsx',
        raw + '/index.ts',
        raw + '/index.tsx',
    }


def find_unresolved_relative_imports(filename: str, content: str, available: set[str]) -> list[str]:
    """Return relative import specifiers that do not resolve to known files."""
    missing = []
    for target in find_relative_imports(content):
        if not (relative_import_candidates(filename, target) & available):
            missing.append(target)
    return missing
