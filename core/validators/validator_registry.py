import os
from .base import CSharpValidator, CValidator, JSValidator, JSONValidator, PHPValidator, PythonValidator, RubyValidator, RustValidator, TextValidator

class ValidatorRegistry:
    def __init__(self):
        self.validators = {
            '.py': PythonValidator(),
            '.js': JSValidator(),
            '.jsx': JSValidator(),
            '.ts': JSValidator(),
            '.tsx': JSValidator(),
            '.rb': RubyValidator(),
            '.rs': RustValidator(),
            '.c': CValidator(),
            '.h': CValidator(),
            '.cs': CSharpValidator(),
            '.csproj': TextValidator(),
            '.sln': TextValidator(),
            '.php': PHPValidator(),
            '.json': JSONValidator()
        }
        self.default_validator = JSValidator() # Baseline structural check
        self.text_validator = TextValidator()

    def validate(self, filename, code, context=None):
        """Elite V10: Runs layered validation (Syntax -> Semantic)."""
        ext = os.path.splitext(filename)[1]
        if filename in {"Makefile", "Dockerfile"}:
            validator = self.text_validator
        else:
            validator = self.validators.get(ext, self.default_validator)
        
        # Layer 1: Syntax
        ok, msg = validator.validate_syntax(code, filename)
        if not ok: return False, f"Syntax Error: {msg}"
        
        # Layer 2: Semantics
        ok, msg = validator.validate_semantics(code, filename, context)
        if not ok: return False, f"Semantic Error: {msg}"
        
        return True, "Valid"
