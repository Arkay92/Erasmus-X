"""
Automatic test generation and execution.
Generates tests based on code, executes them in CLI, and verifies quality.
"""
import os
import subprocess
import re
import json
from typing import Dict, List, Tuple
from core import config

class TestGenerator:
    """Generates and executes tests for generated code."""
    
    def __init__(self, client, local_llm=None):
        self.client = client
        self.local_llm = local_llm
        self.test_results = []
    
    def generate_tests(self, code: str, language: str, file_path: str) -> str:
        """
        Generate tests for a code file.
        
        Args:
            code: Source code
            language: Programming language (python, typescript, go, rust, c)
            file_path: Path to source file
        
        Returns: Test code as string
        """
        print(f"[*] Generating tests for {file_path} ({language})...")
        
        if language == "python":
            return self._generate_python_tests(code, file_path)
        elif language == "typescript" or language == "javascript":
            return self._generate_ts_tests(code, file_path)
        elif language == "go":
            return self._generate_go_tests(code, file_path)
        elif language == "rust":
            return self._generate_rust_tests(code, file_path)
        elif language == "c":
            return self._generate_c_tests(code, file_path)
        else:
            return None
    
    def _generate_python_tests(self, code: str, file_path: str) -> str:
        """Generate Python pytest tests."""
        prompt = f"""Generate pytest tests for this Python code.
        
File: {file_path}
Code:
```python
{code}
```

Requirements:
1. Test each function and class
2. Include happy path and error cases
3. Use pytest fixtures if needed
4. Test edge cases
5. Valid pytest syntax only

Return ONLY the test code, no explanations:"""
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            test_code = response.choices[0].message.content
            # Clean up markdown if present
            test_code = re.sub(r"```python\n?", "", test_code)
            test_code = re.sub(r"```\n?", "", test_code)
            return test_code.strip()
        except Exception as e:
            print(f"[!] Test generation error: {e}")
            return None
    
    def _generate_ts_tests(self, code: str, file_path: str) -> str:
        """Generate TypeScript Jest tests."""
        prompt = f"""Generate Jest tests for this TypeScript code.
        
File: {file_path}
Code:
```typescript
{code}
```

Requirements:
1. Use Jest testing framework
2. Test each exported function and class
3. Include happy path, error cases, and edge cases
4. Mock external dependencies if needed
5. Valid Jest syntax

Return ONLY the test code:"""
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            test_code = response.choices[0].message.content
            test_code = re.sub(r"```typescript\n?", "", test_code)
            test_code = re.sub(r"```\n?", "", test_code)
            return test_code.strip()
        except Exception as e:
            print(f"[!] Test generation error: {e}")
            return None
    
    def _generate_go_tests(self, code: str, file_path: str) -> str:
        """Generate Go testing tests."""
        prompt = f"""Generate Go tests for this code.
        
File: {file_path}
Code:
```go
{code}
```

Use testing.T for unit tests. Valid Go test syntax only."""
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            return None
    
    def _generate_rust_tests(self, code: str, file_path: str) -> str:
        """Generate Rust tests."""
        prompt = f"""Generate Rust tests for this code using #[cfg(test)] modules.
        
Code:
```rust
{code}
```"""
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            return None
    
    def _generate_c_tests(self, code: str, file_path: str) -> str:
        """Generate C unit tests using simple assert pattern."""
        prompt = f"""Generate C unit tests for this code using assert() macro.
        
Code:
```c
{code}
```

Requirements:
- Use <assert.h>
- Test each function
- Include edge cases"""
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            return None
    
    def execute_tests(self, test_file_path: str, language: str) -> Tuple[bool, str]:
        """
        Execute tests and return results.
        
        Returns: (success: bool, output: str)
        """
        print(f"[*] Executing tests: {test_file_path}")
        
        try:
            if language == "python":
                result = subprocess.run(
                    ["python", "-m", "pytest", test_file_path, "-v"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif language == "typescript":
                result = subprocess.run(
                    ["npm", "test", "--", test_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif language == "go":
                result = subprocess.run(
                    ["go", "test", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=os.path.dirname(test_file_path)
                )
            elif language == "rust":
                result = subprocess.run(
                    ["cargo", "test", "--", "--nocapture"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=os.path.dirname(test_file_path)
                )
            elif language == "c":
                # Compile and run C tests
                executable = test_file_path.replace(".c", "")
                compile_result = subprocess.run(
                    ["gcc", test_file_path, "-o", executable],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if compile_result.returncode != 0:
                    return False, f"Compilation error: {compile_result.stderr}"
                
                result = subprocess.run(
                    [executable],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                return False, f"Language '{language}' not supported"
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            self.test_results.append({
                'file': test_file_path,
                'language': language,
                'success': success,
                'output': output[:500]  # Truncate for storage
            })
            
            return success, output
        
        except subprocess.TimeoutExpired:
            return False, "Test execution timed out (30s)"
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    def parse_test_summary(self, output: str) -> Dict:
        """Parse test output to extract metrics."""
        summary = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Look for pytest output
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        error_match = re.search(r'(\d+) error', output)
        skipped_match = re.search(r'(\d+) skipped', output)
        
        if passed_match:
            summary['passed'] = int(passed_match.group(1))
        if failed_match:
            summary['failed'] = int(failed_match.group(1))
        if error_match:
            summary['errors'] = int(error_match.group(1))
        if skipped_match:
            summary['skipped'] = int(skipped_match.group(1))
        
        return summary
    
    def get_report(self) -> str:
        """Generate test report."""
        if not self.test_results:
            return "No tests executed"
        
        report = "=== TEST EXECUTION REPORT ===\n\n"
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results if t['success'])
        
        report += f"Total Test Files: {total_tests}\n"
        report += f"Passed: {passed_tests}/{total_tests}\n"
        report += f"Success Rate: {(passed_tests/total_tests*100):.1f}%\n\n"
        
        for test in self.test_results:
            status = "✓ PASS" if test['success'] else "✗ FAIL"
            report += f"{status} - {test['file']} ({test['language']})\n"
        
        return report
