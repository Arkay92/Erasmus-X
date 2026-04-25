import os
from .base import PythonValidator, JSValidator, RubyValidator, RustValidator, JSONValidator

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
            '.json': JSONValidator()
        }
        self.default_validator = JSValidator() # Baseline structural check

    def validate(self, filename, code, context=None):
        """Elite V10: Runs layered validation (Syntax -> Semantic)."""
        ext = os.path.splitext(filename)[1]
        validator = self.validators.get(ext, self.default_validator)
        
        # Layer 1: Syntax
        ok, msg = validator.validate_syntax(code, filename)
        if not ok: return False, f"Syntax Error: {msg}"
        
        # Layer 2: Semantics
        ok, msg = validator.validate_semantics(code, filename, context)
        if not ok: return False, f"Semantic Error: {msg}"
        
        return True, "Valid"
