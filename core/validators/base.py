import os
import re
import subprocess
import ast
import json
from core.validators.stack_validators import StackValidatorRegistry

class BaseValidator:
    def validate_syntax(self, code, filename):
        """Standard syntax check (Layer 1). Returns (bool, msg)."""
        raise NotImplementedError

    def validate_semantics(self, code, filename, context=None):
        """Framework/Constraint check (Layer 2). Returns (bool, msg)."""
        return True, "N/A"

    def validate_behavior(self, code, filename, output=None):
        """Execution output check (Layer 3). Returns (bool, msg)."""
        return True, "N/A"

class PythonValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        try:
            ast.parse(code)
            return True, "Valid Python Syntax"
        except SyntaxError as e:
            error_type = type(e).__name__
            return False, f"{error_type}: {e.msg} (line {e.lineno})"

    def validate_semantics(self, code, filename, context=None):
        # Elite V9: Deep Import Validation
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and node.exc is None:
                    return False, "Bare raise detected outside explicit exception propagation."
            import sys
            std_libs = getattr(sys, "stdlib_module_names", set())
            if not std_libs:
                import pkgutil
                std_libs = {m.name for m in pkgutil.iter_modules()}
            
            project_modules = {'core', 'utils', 'shards', 'tools'}
            if context and 'available_files' in context:
                project_modules.update({f.replace('.py', '').replace('/', '.').split('.')[0] for f in context['available_files']})

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_mod = alias.name.split('.')[0]
                        if base_mod not in std_libs and base_mod not in project_modules:
                            return False, f"ModuleNotFoundError: Hallucinated import '{alias.name}'"
            return True, "Valid Semantics"
        except Exception as e:
            return False, f"Semantic analysis failed: {e}"

class JSValidator(BaseValidator):
    def __init__(self, stack_registry=None):
        self.stack_registry = stack_registry or StackValidatorRegistry()

    def validate_syntax(self, code, filename):
        # Lightweight brace balancing if node is missing
        if code.count('{') != code.count('}') or code.count('(') != code.count(')'):
             return False, "Potential truncation or imbalanced syntax detected ({} or ())."
             
        # Detect abrupt EOFs (V18 Hardening)
        clean_code = code.strip()
        abrupt_tokens = (
            '=', ',', ':', '+', '-', '*', '/', 'import', 'return', '{', '(', 
            'const', 'let', 'export', 'async', 'function', 'class', 'await', '=>'
        )
        if clean_code.endswith(abrupt_tokens):
             return False, "Syntax Error: Abrupt EOF. File appears visibly truncated."
        
        return True, "Basic syntax check pass"

    def validate_semantics(self, code, filename, context=None):
        # Next.js App Router Contracts
        is_root_layout = filename.endswith('layout.tsx') or filename.endswith('layout.js')
        is_page = filename.endswith('page.tsx') or filename.endswith('page.js')
        is_route = filename.endswith('route.ts') or filename.endswith('route.js')
        
        # Next.js Route Handler Enforcement
        if is_route:
             # Reject named handler habit
             valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}
             invalid_named_handler = re.search(r"export\s+async\s+function\s+([A-Z]+)\s+(\w+)", code)
             if invalid_named_handler:
                  return False, f"Next.js Route Error: Named function '{invalid_named_handler.group(2)}' after HTTP method. Use 'export async function {invalid_named_handler.group(1)}(request: Request)'."
             
             # General check for valid exports
             methods_found = re.findall(r"export\s+async\s+function\s+([a-zA-Z0-9_]+)", code)
             for m in methods_found:
                  if m not in valid_methods and m not in {'config', 'generateStaticParams'}:
                       return False, f"Next.js Route Error: Invalid export '{m}' in route.ts."
             
             # Reject static placeholder routes
             if '{ status: \'ok\'' in code or 'Placeholder API' in code:
                  return False, "Semantic Error: Route handler is a hollow placeholder. Implement actual logic or data handling."

             if 'RequestHTML' in code:
                  return False, "Semantic Error: Invalid type 'RequestHTML' detected. Use 'Request' or 'NextRequest'."

        if is_root_layout:
             if '<html>' not in code or '<body>' not in code:
                  return False, "Next.js Contract Error: Root layout MUST contain <html> and <body> tags."
             if '{children}' not in code and '${children}' not in code:
                  return False, "Next.js Contract Error: Root layout MUST render {children}."
                   
        if (is_root_layout or is_page) and 'export default ' not in code:
              return False, "Next.js Contract Error: Pages and Layouts must have an 'export default' component."
        
        # Elite V13: Detect double default exports
        if len(re.findall(r"export\s+default\s+", code)) > 1:
             return False, "Semantic Error: Multiple 'export default' detected in a single file."

        # Component Depth (Forms)
        if ('Form' in filename or 'login' in filename.lower()) and ('.tsx' in filename or '.jsx' in filename):
             if '<form' not in code or '<input' not in code:
                  return False, f"Semantic Error: '{filename}' appears to be a hollow form shell. Implement real inputs and submission handling."

        # Dependency Graph Validation
        if context and 'available_files' in context:
            valid_bases = {os.path.basename(f).split('.')[0] for f in context['available_files']}
            valid_bases.update({'components', 'lib', 'api', 'app', 'ui', 'hooks', 'utils'})
            
            import_paths = re.findall(r"import\s+.*?\s+from\s+['\"](.*?)['\"]", code)
            for imp in import_paths:
                if imp == 'next/file':
                    return False, f"Semantic Error: Hallucinated import 'next/file' detected."
                if 'next/dist/' in imp:
                    return False, f"Semantic Error: Internal 'next/dist' import detected ('{imp}'). Use public APIs from 'next/'."
                if imp == 'react-router-dom':
                    return False, "Next.js Semantic Error: 'react-router-dom' detected. Use 'next/link' or 'next/navigation'."
                
                # Elite V13: Strict Path Resolution
                if imp.startswith('@/') or imp.startswith('./') or imp.startswith('../'):
                    target_base = os.path.basename(imp).split('.')[0]
                    # Verify if the target exists in available_files
                    # Heuristic: match basename first
                    if target_base not in valid_bases:
                        return False, f"Semantic Error: Unresolved local dependency '{imp}' (not in project manifest)."
                    
                    # Verify relative nesting (Lightweight check: don't allow too many ../)
                    if imp.count('../') > 3:
                         return False, f"Semantic Error: Excessive relative path nesting in '{imp}'."

        # Anti-Laziness Enforcement (Elite V15 Deep Hardening)
        if 'Welcome to your Next.js App' in code and 'app/page.tsx' not in filename and 'app/page.js' not in filename:
             return False, f"Semantic Error: '{filename}' appears to be a lazy copy of the default index page."
        
        # Placeholder Pattern Detection (Aggressive)
        placeholders = [
             r"\[Placeholder.*?\]", 
             r"// logic here", 
             r"// Implement.*?here", 
             r"TODO:.*?Implementation",
             r"return\s+<div.*?>.*?Placeholder.*?</div>",
             r"return\s+null\s+;\s+// logic here",
             r"<h1>Placeholder.*?</h1>",
             r"console\.log\(.*?[pP]laceholder.*?\)",
             r"const\s+\w+\s+=\s+\{\s*\}\s*;\s*//\s*TODO"
        ]
        for p in placeholders:
             if re.search(p, code, re.IGNORECASE):
                  return False, f"Semantic Error: Visual placeholder pattern detected. Provide real implementation."

        if '// TODO' in code or '// In a real app' in code or 'TODO:' in code:
             return False, "Semantic Error: Prototype shortcuts detected (TODO)."
        
        # Elite V17: Junk Path & Package Pollution Guard
        # Rejects filenames that look like packages (e.g. 'sqlite3', 'next-auth/react') 
        # unless they are explicitly in standard framework directories.
        if '/' not in filename and '.' not in filename:
             return False, f"Semantic Error: Target '{filename}' looks like a package or symbol, not a project file."
        
        if '/' in filename and not filename.startswith(('app/', 'components/', 'lib/', 'utils/', 'api/')):
             if '.' not in os.path.basename(filename):
                  return False, f"Semantic Error: '{filename}' appears to be a library import path, not a project file target."

        # Logic Density Enforcement (Elite V19 Hardening)
        # Prevents hollow files with lots of comments but no implementation
        logic_lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith(('/', '*', 'import', 'export', 'type', 'interface'))]
        comment_lines = [l for l in code.splitlines() if l.strip().startswith(('/', '*'))]
        
        if ('lib/' in filename or 'api/' in filename or 'route' in filename or 'page' in filename):
             if len(logic_lines) < 3:
                  return False, f"Semantic Error: '{filename}' is a hollow shell (only {len(logic_lines)} logic lines). Implement real functionality."
             
             if len(comment_lines) > len(logic_lines) * 2 and len(logic_lines) < 10:
                  return False, f"Semantic Error: '{filename}' has excessive comments vs logic. Provide real implementation code."
                  
        # Component Triviality Check
        if ('dashboard' in filename or 'profile' in filename) and ('.tsx' in filename or '.jsx' in filename):
             if code.count('<div') < 2 and 'return' in code:
                  return False, f"Semantic Error: '{filename}' is too trivial for a dashboard/profile component. Implement sub-sections and data displays."
                  
        if 'placeholder = true' in code and 'lib/' in filename:
             return False, "Semantic Error: Library module is a hollow placeholder."

        return self.stack_registry.validate(filename, code, context)

class RubyValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        # Basic check for 'end' count
        if code.count('def ') > code.count('end'):
            return False, "Syntax Error: Missing 'end' for method definition."
        return True, "Basic check pass"

class RustValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        # Basic check for braces and semicolon density
        if code.count('{') != code.count('}'):
             return False, "Imbalanced braces detected."
        return True, "Structural check pass"

class CValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        if code.count('{') != code.count('}'):
             return False, "Imbalanced braces detected."
        if code.count('(') != code.count(')'):
             return False, "Imbalanced parentheses detected."
        return True, "Structural check pass"

class CSharpValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        if code.count('{') != code.count('}'):
             return False, "Imbalanced braces detected."
        if code.count('(') != code.count(')'):
             return False, "Imbalanced parentheses detected."
        return True, "Structural check pass"

class PHPValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        if filename.endswith(".php") and "<?php" not in code:
            return False, "PHP files must start with <?php."
        if code.count('{') != code.count('}'):
             return False, "Imbalanced braces detected."
        if code.count('(') != code.count(')'):
             return False, "Imbalanced parentheses detected."
        return True, "Structural check pass"

class TextValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        if not code.strip():
            return False, "Empty text file."
        return True, "Text file present"

class JSONValidator(BaseValidator):
    def validate_syntax(self, code, filename):
        try:
            json.loads(code)
            return True, "Valid JSON"
        except json.JSONDecodeError as e:
            return False, f"JSON Error: {e.msg} (line {e.lineno})"
