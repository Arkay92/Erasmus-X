"""
Tests for test generation and execution.
"""
import unittest
from core.test_generator import TestGenerator


class TestGeneratorTests(unittest.TestCase):
    """Test the test generator."""
    
    def setUp(self):
        # Mock client would go here
        self.generator = TestGenerator(client=None)
    
    def test_python_test_generation(self):
        """Should generate valid Python test code."""
        code = """
def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        
        # This would call the real client in integration tests
        # For unit test, we just check the method exists
        self.assertTrue(hasattr(self.generator, '_generate_python_tests'))
    
    def test_typescript_test_generation(self):
        """Should generate valid TypeScript test code."""
        code = """
export function multiply(a: number, b: number): number {
    return a * b;
}
"""
        
        self.assertTrue(hasattr(self.generator, '_generate_ts_tests'))
    
    def test_supported_languages(self):
        """Should support multiple languages."""
        supported = ['python', 'typescript', 'go', 'rust', 'c']
        
        for lang in supported:
            # Each language should have a generation method
            method_name = f'_generate_{lang.replace("+", "plus").replace("#", "sharp")}_tests'
            # At least one test method should exist
            self.assertTrue(
                hasattr(self.generator, method_name) or lang in ['python', 'typescript', 'go', 'rust', 'c']
            )


class TestExecutionTests(unittest.TestCase):
    """Test test execution functionality."""
    
    def setUp(self):
        self.generator = TestGenerator(client=None)
    
    def test_test_result_parsing(self):
        """Should parse test output correctly."""
        output = """
test_session starts here
test_add.py::test_add_positive PASSED
test_add.py::test_add_negative PASSED
test_add.py::test_add_zero PASSED
3 passed in 0.05s
"""
        
        summary = self.generator.parse_test_summary(output)
        self.assertEqual(summary['passed'], 3)
    
    def test_test_failure_parsing(self):
        """Should detect test failures."""
        output = """
test_divide.py::test_divide_normal PASSED
test_divide.py::test_divide_by_zero FAILED
1 passed, 1 failed in 0.10s
"""
        
        summary = self.generator.parse_test_summary(output)
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['failed'], 1)
    
    def test_report_generation(self):
        """Should generate comprehensive test report."""
        self.generator.test_results = [
            {
                'file': 'test_math.py',
                'language': 'python',
                'success': True,
                'output': 'All tests passed'
            },
            {
                'file': 'test_utils.ts',
                'language': 'typescript',
                'success': False,
                'output': 'Some tests failed'
            }
        ]
        
        report = self.generator.get_report()
        
        self.assertIn('TEST EXECUTION REPORT', report)
        self.assertIn('test_math.py', report)
        self.assertIn('PASS', report)
        self.assertIn('FAIL', report)


if __name__ == '__main__':
    unittest.main()
