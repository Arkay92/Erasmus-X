"""
Domain-agnostic pack injection system.
Automatically detects missing dependencies from contracts and injects required packs.
"""
import re
import json
from typing import Dict, List, Tuple

class PackInjector:
    """Automatically injects required feature packs based on contract requirements."""
    
    def __init__(self, brain):
        self.brain = brain
        # Map of stack dependencies to required packs
        self.stack_dependencies = {
            "nextjs-app-router": ["layout", "pages"],
            "nextjs-app-router|prisma|typescript": ["prisma", "db", "api-routes"],
            "nextjs-app-router|sqlite|typescript": ["db", "db-sqlite", "api-routes"],
            "react|typescript": ["components", "hooks"],
            "express|typescript": ["middleware", "routes"],
            "fastapi|python": ["models", "routes"],
        }
        
        # Feature dependencies
        self.feature_dependencies = {
            "auth": ["db"],
            "api-tasks": ["db", "validation"],
            "dashboard": ["db"],
            "testing": [],  # No dependencies
        }
    
    def get_required_packs(self, contract: Dict) -> List[str]:
        """
        Analyzes contract and determines which packs MUST be injected.
        
        Returns list of pack names that are missing but required.
        """
        stack = contract.get('stack', '').lower()
        stack_parts = self._split_stack(stack)
        critical_files = contract.get('critical_files', [])
        features = contract.get('features', [])
        
        required_packs = set()
        
        # 1. Stack-based pack requirements
        for stack_pattern, packs in self.stack_dependencies.items():
            pattern_parts = self._split_stack(stack_pattern)
            if pattern_parts and pattern_parts.issubset(stack_parts):
                required_packs.update(packs)
        
        # 2. Feature-based pack requirements
        for feature in features:
            if feature in self.feature_dependencies:
                required_packs.update(self.feature_dependencies[feature])
        
        # 3. Critical file-based pack inference
        for cf in critical_files:
            if "api/" in cf:
                required_packs.add("api-routes")
            if "db" in cf.lower() or "prisma" in cf.lower():
                if "prisma" in stack:
                    required_packs.add("prisma")
                else:
                    required_packs.add("db")
            if "auth" in cf.lower():
                required_packs.add("auth")
        
        return sorted(required_packs)

    def _split_stack(self, stack: str) -> set:
        return {part.strip() for part in re.split(r"[|,\s]+", stack.lower()) if part.strip()}
    
    def inject_packs(self, contract: Dict, file_map: Dict) -> Tuple[List[str], Dict]:
        """
        Injects missing packs into the file_map.
        
        Returns (list of injected pack names, updated file_map)
        """
        missing_packs = self.get_required_packs(contract)
        injected = []
        
        for pack_name in missing_packs:
            pack = self.brain.get_feature_pack(pack_name)
            if pack:
                # Inject all files from the pack
                for file_data in pack.get('files', []):
                    path = file_data.get('path', '')
                    content = file_data.get('content', '')
                    if path and path not in file_map:
                        file_map[path] = content
                        injected.append(path)
                print(f"[+] Pack Injector: Injected pack '{pack_name}' with {len(pack.get('files', []))} files")
        
        return injected, file_map
    
    def validate_contract_coherence(self, contract: Dict, file_map: Dict) -> Tuple[bool, List[str]]:
        """
        Validates that contract and implementation are coherent.
        
        Returns (is_coherent, list of violations)
        """
        violations = []
        stack = contract.get('stack', '').lower()
        
        # Check 1: Prisma in contract but SQLite in code
        if 'prisma' in stack:
            for path, content in file_map.items():
                if 'sqlite' in content.lower() and 'better-sqlite3' in content:
                    if '@prisma/client' not in content and 'prisma' not in content.lower():
                        violations.append(f"CONTRACT VIOLATION: {path} uses SQLite3 but contract requires Prisma")
        
        # Check 2: Database layer consistency
        db_files = [p for p in file_map.keys() if 'db.' in p or 'database' in p.lower()]
        if db_files:
            content = file_map.get(db_files[0], '')
            for path, code in file_map.items():
                if 'execute(' in code or 'query(' in code:
                    if 'prisma' in stack and '@prisma/client' not in content:
                        violations.append(f"DATABASE LAYER MISMATCH: {path} uses raw query but contract mandates Prisma ORM")
        
        # Check 3: API routes that depend on missing DB
        api_routes = [p for p in file_map.keys() if '/api/' in p or '/route' in p]
        has_db = any('db' in p.lower() for p in file_map.keys())
        if api_routes and not has_db:
            violations.append("MISSING DB LAYER: API routes exist but no database module found")
        
        return len(violations) == 0, violations
