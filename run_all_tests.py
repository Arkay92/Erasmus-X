import unittest
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def run_suite(directory, pattern='test_*.py'):
    print(f"\n>>> Running tests in: {directory} (Pattern: {pattern})")
    loader = unittest.TestLoader()
    suite = loader.discover(directory, pattern=pattern)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)

if __name__ == '__main__':
    print("="*60)
    print("      ERASMUS CELL COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    test_root = os.path.dirname(os.path.abspath(__file__))
    directories = [
        os.path.join(test_root, 'test', 'unit'),
        os.path.join(test_root, 'test', 'integration'),
        os.path.join(test_root, 'test', 'acceptance')
    ]
    
    overall_success = True
    for d in directories:
        if os.path.exists(d):
            result = run_suite(d)
            if not result.wasSuccessful():
                overall_success = False
        else:
            print(f"[!] Warning: Directory {d} not found.")

    print("\n" + "="*60)
    if overall_success:
        print("  [SUCCESS] ALL TEST STAGES PASSED SUCCESSFULLY")
    else:
        print("  [FAILURE] SOME TEST STAGES FAILED")
    print("="*60)
    
    sys.exit(0 if overall_success else 1)
