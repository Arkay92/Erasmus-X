import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.validators.validator_registry import ValidatorRegistry

class TestValidators(unittest.TestCase):
    def setUp(self):
        self.registry = ValidatorRegistry()

    def test_python_syntax_validator(self):
        filename = "test.py"
        valid_code = "def hello():\n    print('world')"
        invalid_code = "def hello():\nprint('world')" # Indentation error
        
        ok, err = self.registry.validate(filename, valid_code)
        self.assertTrue(ok)
        
        ok, err = self.registry.validate(filename, invalid_code)
        self.assertFalse(ok)
        self.assertIn("IndentationError", err)

    def test_json_validator(self):
        filename = "config.json"
        valid_json = '{"key": "value"}'
        invalid_json = '{"key": "value",}' # Trailing comma
        
        ok, err = self.registry.validate(filename, valid_json)
        self.assertTrue(ok)
        
        ok, err = self.registry.validate(filename, invalid_json)
        self.assertFalse(ok)
        self.assertIn("JSON", err)

if __name__ == '__main__':
    unittest.main()
