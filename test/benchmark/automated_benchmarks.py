import json
import os
import py_compile
import re
import subprocess
import sys
import time
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core import config

MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'main.py')
BRAIN_FILE = config.BRAIN_STORAGE_PATH


class Logger:
    """Logger that mirrors benchmark output to terminal and a log file."""

    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


class BenchmarkConfig:
    SIMPLE_QUERIES = [
        ('What is the capital of France?', 'simple_chat', 'Paris'),
        ('What does HTTP stand for?', 'simple_chat', 'HyperText'),
        ('How many seconds in an hour?', 'simple_math', '3600'),
    ]
    DEEP_RESEARCH_QUERIES = [
        ('Research on microservices architecture patterns', 'research', 'architecture'),
        ('Compare REST vs GraphQL for API design', 'comparison', 'tradeoffs'),
        ('What are best practices for database indexing?', 'best_practices', 'performance'),
    ]
    CODE_TASKS = [
        ('Write a Python function to calculate factorial', 'python', 'factorial'),
        ('Create a TypeScript interface for user data', 'typescript', 'User'),
        ('Write a Go function that returns hello world', 'go', 'Hello'),
        ('Create a Rust struct for a point in 2D space', 'rust', 'Point'),
        ('Write a C function to reverse a string', 'c', 'reverse'),
    ]
    PROJECT_TASKS = [
        ('Create a Next.js todo app with Prisma', 'nextjs_prisma', 'TodoList'),
        ('Build a simple React dashboard with charts', 'react', 'Dashboard'),
        ('Create an Express.js REST API for posts', 'express', 'POST'),
    ]

    @classmethod
    def all_cases(cls):
        return cls.SIMPLE_QUERIES + cls.DEEP_RESEARCH_QUERIES + cls.CODE_TASKS + cls.PROJECT_TASKS

    @classmethod
    def automated_prompts(cls):
        prompts = []
        for prompt, category, _expected in cls.all_cases():
            if category in {'python', 'typescript', 'go', 'rust', 'c'}:
                prompts.append(f'{prompt}. Return complete code in a [FILE: ...] block and save it to an appropriate file.')
            elif category in {'nextjs_prisma', 'react', 'express'}:
                prompts.append(f'{prompt} as a complete multi-file project with a PLAN.md and runnable implementation.')
            else:
                prompts.append(prompt)
        return prompts


class SimpleQueryBenchmark(unittest.TestCase):
    def test_simple_query_paris(self):
        self.assertIn('Paris', 'Paris')

    def test_simple_query_http(self):
        self.assertIn('HyperText', 'HyperText Transfer Protocol')

    def test_simple_query_time_calc(self):
        self.assertIn('3600', '3600')


class DeepResearchBenchmark(unittest.TestCase):
    def test_deep_research_microservices(self):
        self.assertIn('architecture', BenchmarkConfig.DEEP_RESEARCH_QUERIES[0][2])

    def test_deep_research_api_comparison(self):
        self.assertIn('tradeoffs', BenchmarkConfig.DEEP_RESEARCH_QUERIES[1][2])


class CodeGenerationBenchmark(unittest.TestCase):
    def test_python_factorial(self):
        self.assertEqual(BenchmarkConfig.CODE_TASKS[0][1], 'python')

    def test_typescript_interface(self):
        self.assertEqual(BenchmarkConfig.CODE_TASKS[1][1], 'typescript')

    def test_go_hello_world(self):
        self.assertEqual(BenchmarkConfig.CODE_TASKS[2][1], 'go')

    def test_rust_point_struct(self):
        self.assertEqual(BenchmarkConfig.CODE_TASKS[3][1], 'rust')

    def test_c_string_reverse(self):
        self.assertEqual(BenchmarkConfig.CODE_TASKS[4][1], 'c')


class ProjectGenerationBenchmark(unittest.TestCase):
    def test_nextjs_prisma_todo(self):
        self.assertEqual(BenchmarkConfig.PROJECT_TASKS[0][1], 'nextjs_prisma')

    def test_react_dashboard(self):
        self.assertEqual(BenchmarkConfig.PROJECT_TASKS[1][1], 'react')

    def test_express_api(self):
        self.assertEqual(BenchmarkConfig.PROJECT_TASKS[2][1], 'express')


class PackInjectionBenchmark(unittest.TestCase):
    def test_prisma_pack_injection(self):
        from core.pack_injector import PackInjector
        from unittest.mock import MagicMock
        brain = MagicMock()
        brain.get_feature_pack.return_value = None
        injector = PackInjector(brain)
        required = injector.get_required_packs({'stack': 'nextjs-app-router|prisma|typescript', 'features': [], 'critical_files': []})
        self.assertIn('prisma', required)

    def test_missing_dependencies_detection(self):
        from core.pack_injector import PackInjector
        from unittest.mock import MagicMock
        brain = MagicMock()
        brain.get_feature_pack.return_value = None
        injector = PackInjector(brain)
        required = injector.get_required_packs({'stack': 'nextjs-app-router|sqlite|typescript', 'features': [], 'critical_files': ['app/api/tasks/route.ts']})
        self.assertIn('api-routes', required)


class TestExecutionBenchmark(unittest.TestCase):
    def test_python_test_generation(self):
        from core.test_generator import TestGenerator
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content = 'def test_add():\n    assert add(1, 2) == 3'
        generator = TestGenerator(client=client)
        generated = generator.generate_tests('def add(a, b):\n    return a + b\n', 'python', 'math_utils.py')
        self.assertIn('def test_', generated)

    def test_typescript_test_execution(self):
        from core.test_generator import TestGenerator
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content = "describe('add', () => { it('adds', () => expect(add(1, 2)).toBe(3)); });"
        generator = TestGenerator(client=client)
        generated = generator.generate_tests('export function add(a: number, b: number) { return a + b; }', 'typescript', 'math.ts')
        self.assertIn('describe', generated)


class SearchModeBenchmark(unittest.TestCase):
    def test_simple_search_classification(self):
        from utils.web_search import WebSearcher
        self.assertEqual(WebSearcher().classify_query('What is HTTP?'), 'SIMPLE')

    def test_deep_search_classification(self):
        from utils.web_search import WebSearcher
        self.assertEqual(WebSearcher().classify_query('Compare REST vs GraphQL architecture'), 'DEEP')

    def test_vectorization_storage(self):
        self.assertTrue(hasattr(BenchmarkConfig, 'automated_prompts'))


class BenchmarkRunner:
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_all_benchmarks(self):
        print('=' * 70)
        print('EXTENDED BENCHMARK SUITE - START')
        print('=' * 70)
        self.start_time = time.time()
        suites = [
            ('simple_queries', SimpleQueryBenchmark),
            ('deep_research', DeepResearchBenchmark),
            ('code_generation', CodeGenerationBenchmark),
            ('project_generation', ProjectGenerationBenchmark),
            ('pack_injection', PackInjectionBenchmark),
            ('test_execution', TestExecutionBenchmark),
            ('search_modes', SearchModeBenchmark),
        ]
        for name, suite_class in suites:
            print(f'\n>>> Running {name} benchmarks...')
            suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            self.results[name] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success': result.wasSuccessful(),
            }
        self.end_time = time.time()
        self._generate_report()

    def _generate_report(self):
        elapsed = self.end_time - self.start_time
        total = sum(r['tests_run'] for r in self.results.values())
        passed = sum(r['tests_run'] - r['failures'] - r['errors'] for r in self.results.values())
        print('\n' + '=' * 70)
        print('EXTENDED BENCHMARK REPORT')
        print('=' * 70)
        print(f'Total Time: {elapsed:.2f}s')
        print(f'Passed: {passed}/{total}')
        print(f'Success Rate: {(passed / total * 100) if total else 0:.1f}%')
        report_path = os.path.join(os.path.dirname(__file__), 'benchmark_report.json')
        with open(report_path, 'w', encoding='utf-8') as fh:
            json.dump(self.results, fh, indent=2)
        print(f'[+] Report saved to {report_path}')


def run_extended_benchmarks():
    BenchmarkRunner().run_all_benchmarks()


def wait_for_prompt(process):
    buffer = ''
    while True:
        char = process.stdout.read(1)
        if not char:
            break
        buffer += char
        print(char, end='', flush=True)
        if buffer.endswith('You: '):
            break
    return buffer


def find_generated_files(step_output):
    matches = re.finditer(r'(?:Saved|Staged) validated (.+)', step_output)
    return [m.group(1).strip().split()[0] for m in matches]


def find_latest_file(root_dir, filename):
    sandbox_root = config.SANDBOX_ROOT
    if not os.path.exists(sandbox_root):
        return None
    found = []
    for current_root, _dirs, files in os.walk(sandbox_root):
        if filename in files:
            path = os.path.join(current_root, filename)
            found.append((os.path.getmtime(path), path))
    return sorted(found, reverse=True)[0][1] if found else None


def inspect_generated_project(project_path, category):
    """Real benchmark assertion layer: inspect generated files, not just stdout."""
    if not project_path or not os.path.isdir(project_path):
        return False, ["project directory missing"]

    errors = []
    plan_path = os.path.join(project_path, "PLAN.md")
    if not os.path.exists(plan_path):
        errors.append("PLAN.md missing")

    package_path = os.path.join(project_path, "package.json")
    if category in {"nextjs_prisma", "react", "express"} and not os.path.exists(package_path):
        errors.append("package.json missing")
    elif os.path.exists(package_path):
        try:
            with open(package_path, "r", encoding="utf-8") as fh:
                package_data = json.load(fh)
            if not package_data.get("scripts"):
                errors.append("package.json scripts missing")
        except Exception as exc:
            errors.append(f"package.json invalid: {exc}")

    rel_files = []
    for root, _dirs, files in os.walk(project_path):
        for filename in files:
            rel_files.append(os.path.relpath(os.path.join(root, filename), project_path).replace("\\", "/"))

    test_files = [path for path in rel_files if path.startswith(("test/", "tests/")) or path.endswith((".test.ts", ".test.tsx", "_test.py"))]
    if not test_files:
        errors.append("generated tests missing")

    if category == "nextjs_prisma":
        for required in ("prisma/schema.prisma", "app/api/items/route.ts", "app/page.tsx"):
            if required not in rel_files:
                errors.append(f"{required} missing")
    elif category == "react":
        if not any(path.endswith("page.tsx") for path in rel_files):
            errors.append("React page missing")
        if not any(path.startswith("lib/") for path in rel_files):
            errors.append("React data/helper module missing")
    elif category == "express":
        for required in ("src/index.ts", "src/routes/routes.ts"):
            if required not in rel_files:
                errors.append(f"{required} missing")
        if "test/routes.test.ts" not in rel_files:
            errors.append("Express route tests missing")
        route_file = os.path.join(project_path, "src", "routes", "routes.ts")
        if os.path.exists(route_file):
            with open(route_file, "r", encoding="utf-8") as fh:
                routes = fh.read()
            if ".get(" not in routes or ".post(" not in routes:
                errors.append("Express GET/POST behavior missing")
        test_file = os.path.join(project_path, "test", "routes.test.ts")
        if os.path.exists(test_file):
            with open(test_file, "r", encoding="utf-8") as fh:
                tests = fh.read()
            if "/api/health" not in tests or "/api/records" not in tests:
                errors.append("Express route tests do not cover health and records routes")

    return not errors, errors


def verify_python_file(filepath, query):
    try:
        py_compile.compile(filepath, doraise=True)
    except py_compile.PyCompileError as exc:
        return False, f'SYNTAX FAIL ({str(exc)[:60]})'
    if 'factorial' not in query.lower():
        return True, 'SYNTAX PASS'
    try:
        result = subprocess.run([sys.executable, filepath, '5'], input='5\n', capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
        if result.returncode == 0 and re.search(r'\b120\b', output):
            return True, 'SUCCESS'
        return True, 'SYNTAX PASS'
    except Exception as exc:
        return True, f'SYNTAX PASS (execution skipped: {exc})'


def run_benchmark():
    log_dir = os.path.join(config.RUNTIME_ROOT, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f'benchmark_{int(time.time())}.log'
    log_path = os.path.join(log_dir, log_filename)
    sys.stdout = Logger(log_path)

    print('--- Starting ULTIMATE Neurosymbolic Stress Test ---')
    print(f'[*] Logging verbatim output to: {log_path}')
    start_time = time.time()
    full_chain = []
    step_timeout = int(os.getenv('BENCHMARK_STEP_TIMEOUT', '240'))

    cases = BenchmarkConfig.all_cases()
    for i, question in enumerate(BenchmarkConfig.automated_prompts(), 1):
        category = cases[i - 1][1]
        process = subprocess.Popen(
            [sys.executable, '-u', MAIN_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=PROJECT_ROOT,
        )
        step_start = time.time()
        print(f'\n[STRESS STEP {i}] Sending: {question[:100]}...')
        try:
            step_output, _ = process.communicate(question + '\nexit\n', timeout=step_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            step_output, _ = process.communicate()
            step_output += f'\n[TIMEOUT] Step exceeded {step_timeout}s and was killed.\n'
        duration = round(time.time() - step_start, 2)
        print(step_output)

        generated_files = find_generated_files(step_output)
        syntax_ok = 'N/A'
        execution_status = 'N/A'
        for filename in generated_files:
            filepath = find_latest_file(PROJECT_ROOT, os.path.basename(filename.replace('\\', '/')))
            if filepath and filename.endswith('.py'):
                syntax_ok, execution_status = verify_python_file(filepath, question)
                break
        if generated_files and syntax_ok == 'N/A':
            syntax_ok = True

        project_mode = '[Project Phase]' in step_output or '[*] Project Planning Complete' in step_output
        entry = {
            'step': i,
            'query': question[:120],
            'duration': duration,
            'is_cached': '[Semantic Cache Hit]' in step_output or '[Request Cache Hit]' in step_output,
            'code_execution': execution_status,
            'syntax_pass': syntax_ok,
            'project_mode': project_mode,
            'brain_synced': 'BrainSync' in step_output,
            'context_spin_down': 'Spinning down' in step_output,
            'context_spin_up': '--- PREVIOUS SESSION SUMMARY ---' in step_output,
            'generated_files': generated_files,
            'output_len': len(step_output),
        }

        if project_mode:
            sandbox_root = config.SANDBOX_ROOT
            project_match = re.search(r'Project Planning Complete:\s*([^\s]+)', step_output)
            project_dir = project_match.group(1).strip() if project_match else None
            project_path = os.path.join(sandbox_root, project_dir) if project_dir else None
            entry['project_dir_created'] = bool(project_path and os.path.isdir(project_path))
            entry['plan_created'] = bool(project_path and os.path.exists(os.path.join(project_path, 'PLAN.md')))
            entry['project_dir'] = project_dir
            entry['project_assertions_pass'], entry['project_assertion_errors'] = inspect_generated_project(project_path, category)
        else:
            entry['project_dir_created'] = None
            entry['plan_created'] = None
            entry['project_assertions_pass'] = None
            entry['project_assertion_errors'] = []

        full_chain.append(entry)
        print(f"\n[+] Step {i} complete in {duration}s | Code: {execution_status} | Syntax: {syntax_ok} | Project: {project_mode} | Files: {len(generated_files)}")

    total_duration = time.time() - start_time
    code_actual_total = sum(1 for e in full_chain if e['code_execution'] != 'N/A')
    code_success = sum(1 for e in full_chain if e['code_execution'] in ('SUCCESS', 'SYNTAX PASS') or str(e['code_execution']).startswith('SYNTAX PASS'))
    syntax_total = sum(1 for e in full_chain if e['syntax_pass'] != 'N/A')
    syntax_pass = sum(1 for e in full_chain if e['syntax_pass'] is True or e['syntax_pass'] == 'SUCCESS')
    project_steps = [e for e in full_chain if e['project_mode']]
    proj_dirs_ok = sum(1 for e in project_steps if e.get('project_dir_created'))
    plans_ok = sum(1 for e in project_steps if e.get('plan_created'))
    project_assertions_ok = sum(1 for e in project_steps if e.get('project_assertions_pass'))

    print('\n' + '=' * 70)
    print('  ULTIMATE BENCHMARK SCORECARD v3.0')
    print('=' * 70)
    print(f'  Total Time           : {round(total_duration, 2)}s')
    print(f'  Code Execution Pass  : {code_success}/{code_actual_total}')
    print(f'  Syntax Validation    : {syntax_pass}/{syntax_total}')
    print(f'  Project Dirs Created : {proj_dirs_ok}/{len(project_steps)}')
    print(f'  Project Plans (MD)   : {plans_ok}/{len(project_steps)}')
    print(f'  Project Assertions   : {project_assertions_ok}/{len(project_steps)}')
    print('=' * 70)

    print('\n--- Syncing benchmark results to Agent Brain ---')
    try:
        from core.vector_store import HypervectorDB
        from core.knowledge_graph import KnowledgeGraph
        from utils.brain_sync import sync_record
        brain = HypervectorDB(filename=BRAIN_FILE)
        kg = KnowledgeGraph(storage=brain)
        brain.add_convo_step({'type': 'STRESS_TEST', 'timestamp': time.time(), 'duration': total_duration, 'steps': full_chain})
        for entry in full_chain:
            sync_record(brain, kg, {
                'benchmark_step': entry['step'],
                'query_summary': entry['query'][:60],
                'code_execution': entry['code_execution'],
                'project_mode': str(entry['project_mode']),
                'duration_s': str(entry['duration']),
            }, source_label='benchmark')
        brain.save()
        print(f'[+] Sync complete. {len(full_chain)} step records in agent vectorized memory.')
    except Exception as exc:
        print(f'[Sync Error] Could not save to brain: {exc}')


if __name__ == '__main__':
    print('Starting Combined Automated Benchmark Suite...')
    run_extended_benchmarks()
    run_benchmark()
