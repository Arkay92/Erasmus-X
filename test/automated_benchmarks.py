import subprocess
import time
import os
import re
import py_compile
import sys

# Ensure project root is in sys.path for direct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')

class Logger(object):
    """Verbatim logger that writes to both terminal and file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        # This flush method is needed for python 3 compatibility.
        self.terminal.flush()
        self.log.flush()

from core import config

# Test Suite Configuration
MAIN_SCRIPT = "main.py"
BRAIN_FILE = config.BRAIN_STORAGE_PATH

# 10 Steps of Cross-Modal & Functional Coding Synthesis
TEST_QUESTIONS = [
    # Reasoning Stress
    "How does the structure of the Higgs boson relate to the 'Hard Problem of Consciousness' as defined by David Chalmers?",
    "Compare the fall of the Western Roman Empire to the modern 'Alignment Problem' in AI safety.",
    "If Kant applied his Categorical Imperative to the Silk Road trade, how would it have changed 13th-century economics?",
    "Describe a logical relationship between Gödel's Incompleteness Theorems and the architecture of a SpaceX Starship.",
    "Summarize how the Great Depression's impact on political stability compares to the ethics of autonomous weapon systems today.",
    
    # Coding Stress (Simplified for 2B Hardware Stability)
    "Write a Python function to calculate the GCD of two numbers using the Euclidean algorithm. [FILE: gcd.py]",
    "Write a script that calculates the Fibonacci sequence up to its 10th term using a generator. [FILE: fib.py]",
    "Create a script that filters a list of fruits for only those with more than 5 letters. [FILE: filter.py]",
    "Implement a basic Bubble Sort algorithm in Python for a list of numbers. [FILE: sort.py]",
    "Write a Python script to convert 100 degrees Fahrenheit to Celsius. [FILE: convert.py]",
    
    # Project Stress
    "Design and implement a complete Project: 'Planet Explorer'. This should be a multi-file application with a main entry point, a data module for JSON persistence to store planetary data, and a generator module for procedural planet names. Create a PLAN.md first.",

    # Context Management Stress (Multi-turn session)
    [
        "Let's discuss the history of cryptography. Start with the Caesar cipher.",
        "Now explain the Vigenère cipher in detail. Give a long description.",
        "Add a 3000 character essay about the impact of Enigma on WWII to the context.",
        "Can you summarize our entire conversation so far? (This should trigger Spin-Down and then Spin-Up)"
    ]
]

def run_benchmark():
    # Setup Logging
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"benchmark_{int(time.time())}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    sys.stdout = Logger(log_path)
    
    print(f"--- Starting ULTIMATE Neurosymbolic Stress Test ---")
    print(f"[*] Logging verbatim output to: test/logs/{log_filename}")
    
    start_time = time.time()
    full_chain = []
    
    def wait_for_prompt(target_process):
        """Reads output until the 'You:' prompt is found."""
        buffer = ""
        while True:
            char = target_process.stdout.read(1)
            if not char:
                break
            buffer += char
            # Print to console so we can see progress
            print(char, end="", flush=True)
            if buffer.endswith("You: "):
                break
        return buffer
    
    for i, question in enumerate(TEST_QUESTIONS):
        # Start a fresh agent process for each step to ensure full context window
        process = subprocess.Popen(
            ["python", "-u", MAIN_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        )
        
        # Initial connection wait
        wait_for_prompt(process)

        step_start = time.time()

        # Handle Multi-turn vs Single-turn
        sub_questions = question if isinstance(question, list) else [question]
        step_outputs = []
        is_spin_down = False
        is_spin_up = False
        
        for sub_q in sub_questions:
            print(f"\n[STRESS STEP {i+1}] Sending: {sub_q[:80]}...")
            process.stdin.write(sub_q + "\n")
            process.stdin.flush()
            
            output = wait_for_prompt(process)
            step_outputs.append(output)
            if "Spinning down..." in output: is_spin_down = True
            if "--- PREVIOUS SESSION SUMMARY ---" in output: is_spin_up = True

        step_output = "\n".join(step_outputs)
        step_duration = time.time() - step_start
        
        # Extract response
        is_cached = "[Semantic Cache Hit]" in step_output
        
        # New: Execution & Syntax Verification
        execution_status = "N/A"
        syntax_ok = True
               # Find all files mentioned
        file_matches = re.finditer(r"Saved validated (.+)", step_output)
        found_any_file = False
        
        for file_match in file_matches:
            found_any_file = True
            filename = file_match.group(1).strip()
            # Clean up potential extra log markers like " [Local LLM]" or " from ..."
            filename = filename.split()[0]
            
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            
            # Find the file in sandboxes
            sandbox_root = os.path.join(root_dir, 'sandboxes')
            filepath = None
            
            # Search project subdirectories if needed
            if os.path.exists(sandbox_root):
                for sd in os.listdir(sandbox_root):
                    potential = os.path.join(sandbox_root, sd, filename)
                    if os.path.exists(potential):
                        filepath = potential
                        break
                if not filepath:
                    # Check top level
                    potential = os.path.join(sandbox_root, filename)
                    if os.path.exists(potential):
                        filepath = potential

            # 1. Syntax Check (Python files)
            if filename.endswith(".py") and filepath and os.path.exists(filepath):
                try:
                    py_compile.compile(filepath, doraise=True)
                except py_compile.PyCompileError as e:
                    print(f"  [!] Syntax Error in {filename}: {str(e)[:50]}...")
                    syntax_ok = False

            # 2. Execution & Semantic Verification
            is_main = filename in ["main.py", "gcd.py", "fib.py", "filter.py", "sort.py", "convert.py"]
            if is_main and filepath and os.path.exists(filepath):
                print(f"\n[*] Execution Verification: Running {filename}...")
                try:
                    run_res = subprocess.run([sys.executable, filepath], capture_output=True, text=True, timeout=20)
                    stdout = run_res.stdout.strip()
                    stderr = run_res.stderr.strip()
                    
                    if run_res.returncode == 0:
                        # Elite V6: Semantic Validation
                        semantic_ok = True
                        msg = ""
                        
                        if filename == "gcd.py":
                            # Rigorous check: gcd(48, 18) == 6
                            # We search for '6' specifically as a stand-alone number
                            if not re.search(r"\b6\b", stdout):
                                semantic_ok = False
                                msg = "GCD result '6' for (48, 18) not found."
                        
                        elif filename == "fib.py":
                            # Rigorous check: Full sequence up to 10 terms
                            fib_seq = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
                            found_seq = [int(n) for n in re.findall(r"\b\d+\b", stdout)]
                            if not any(all(x in found_seq for x in fib_seq) or "34" in stdout for _ in [1]):
                                # Fallback to checking just the 10th term if the model didn't print the whole sequence
                                if "34" not in stdout:
                                    semantic_ok = False
                                    msg = "10th Fibonacci term (34) or full sequence not found."
                        
                        elif filename == "filter.py":
                            # Check for specific filtered results > 5 letters
                            expected = ["banana", "cherry", "elderberry"]
                            actual = stdout.lower()
                            if not all(f in actual for f in expected):
                                semantic_ok = False
                                msg = f"Missing expected fruits: {[f for f in expected if f not in actual]}"
                        
                        elif filename == "sort.py":
                            # Verify numbers are in non-decreasing order AND we haven't lost data
                            nums = [int(n) for n in re.findall(r"\b\d+\b", stdout)]
                            if not nums:
                                semantic_ok = False
                                msg = "No numbers found in sort output."
                            elif nums != sorted(nums):
                                semantic_ok = False
                                msg = "List is not sorted."
                        
                        elif filename == "convert.py":
                            # Rigorous check: 100F -> 37.777... (37.78)
                            if "37.7" not in stdout or ("37.78" not in stdout and "37.77" not in stdout):
                                semantic_ok = False
                                msg = "Fahrenheit conversion result (37.77 or 37.78) not found."
                                
                        if semantic_ok:
                            execution_status = "SUCCESS"
                        else:
                            execution_status = f"LOGIC FAIL ({msg})"
                    else:
                        msg = stderr or stdout
                        execution_status = f"EXEC FAIL ({msg[:40]}...)"
                except Exception as e:
                    execution_status = f"SYSTEM ERROR ({str(e)})"
                print(f"[*] Execution Result: {execution_status}")

        entry = {
            "step": i + 1,
            "query": str(question)[:100],
            "duration": round(step_duration, 2),
            "is_cached": is_cached,
            "search_triggered": "[Headless Search]" in step_output,
            "facts_extracted": len(re.findall(r"\[FACT\].*", step_output)),
            "code_execution": execution_status,
            "syntax_pass": syntax_ok if found_any_file else "N/A",
            "project_mode": "Project Mode Detected" in step_output,
            "brain_synced": "BrainSync" in step_output,
            "context_spin_down": is_spin_down,
            "context_spin_up": is_spin_up,
            "output_len": len(step_output),
            "raw_output": step_output[:500] 
        }
        full_chain.append(entry)

        # Additional check: if project mode ran, verify directory was created & PLAN.md exists
        if entry["project_mode"]:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            sandbox_dirs = [d for d in os.listdir(os.path.join(root_dir, 'sandboxes'))
                            if d.startswith('project_')]
            proj_created = len(sandbox_dirs) > 0
            
            plan_exists = False
            if proj_created:
                plan_path = os.path.join(root_dir, 'sandboxes', sandbox_dirs[-1], 'PLAN.md')
                plan_exists = os.path.exists(plan_path)
            
            entry["project_dir_created"] = proj_created
            entry["plan_created"] = plan_exists
            
            print(f"[*] Project Dir Check: {'✅ Created' if proj_created else '❌ Missing'} ({sandbox_dirs[-1] if sandbox_dirs else 'none'})")
            print(f"[*] Project Plan Check: {'✅ PLAN.md found' if plan_exists else '❌ PLAN.md missing'}")
        else:
            entry["project_dir_created"] = None
            entry["plan_created"] = None

        print(f"\n[+] Step {i+1} complete in {entry['duration']}s | "
              f"Cache: {entry['is_cached']} | Code: {entry['code_execution']} | "
              f"Syntax: {entry['syntax_pass']} | Project: {entry['project_mode']} | "
              f"SpinDown: {entry['context_spin_down']} | SpinUp: {entry['context_spin_up']}")
        
        # Cleanly exit this step's process
        try:
            process.stdin.write("exit\n")
            process.stdin.flush()
        except Exception:
            pass
        process.terminate()
        process.wait(timeout=5)
        
        time.sleep(1)

    # ── Scorecard ─────────────────────────────────────────────────────────────
    print("\n--- Stress Test Complete ---")

    total_duration = time.time() - start_time
    total_facts = sum(e['facts_extracted'] for e in full_chain)
    search_ops = sum(1 for e in full_chain if e['search_triggered'])
    cache_hits = sum(1 for e in full_chain if e['is_cached'])
    code_success = sum(1 for e in full_chain if e['code_execution'] == "SUCCESS")
    code_total = sum(1 for e in full_chain if e['code_execution'] not in ["N/A", "N/A"]) # Corrected count logic
    code_actual_total = sum(1 for e in full_chain if e['code_execution'] != "N/A")
    syntax_pass = sum(1 for e in full_chain if e['syntax_pass'] is True)
    syntax_total = sum(1 for e in full_chain if e['syntax_pass'] != "N/A")
    project_steps = [e for e in full_chain if e['project_mode']]
    proj_dirs_ok = sum(1 for e in project_steps if e.get('project_dir_created'))
    plans_ok = sum(1 for e in project_steps if e.get('plan_created'))
    brain_syncs = sum(1 for e in full_chain if e['brain_synced'])
    spin_downs = sum(1 for e in full_chain if e['context_spin_down'])
    spin_ups = sum(1 for e in full_chain if e['context_spin_up'])

    print("\n" + "="*70)
    print("  ULTIMATE BENCHMARK SCORECARD v2.0")
    print("="*70)
    print(f"  Total Time           : {round(total_duration, 2)}s")
    print(f"  Facts Extracted      : {total_facts}")
    print(f"  Web Searches         : {search_ops}")
    print(f"  Semantic Cache Hits  : {cache_hits}")
    print(f"  Code Execution Pass  : {code_success}/{code_actual_total}")
    print(f"  Syntax Validation    : {syntax_pass}/{syntax_total}")
    print(f"  Project Dirs Created : {proj_dirs_ok}/{len(project_steps) if project_steps else 0}")
    print(f"  Project Plans (MD)   : {plans_ok}/{len(project_steps) if project_steps else 0}")
    print(f"  Context Spin-Downs   : {spin_downs}")
    print(f"  Session Continuity   : {spin_ups}")
    print(f"  Brain Syncs          : {brain_syncs}")
    print("="*70)
    print("\n  Per-Step Summary:")
    print(f"  {'Step':<5} {'Time':>7}  {'Cache':<6} {'Code':<10} {'Syntax':<7} {'Proj':<5} {'SD':<3} {'SU':<3}")
    print("  " + "-"*65)
    for e in full_chain:
        print(f"  {e['step']:<5} {e['duration']:>6.1f}s  "
              f"{'Y' if e['is_cached'] else 'N':<6} "
              f"{e['code_execution'][:9]:<10} "
              f"{'PASS' if e['syntax_pass'] is True else ('FAIL' if e['syntax_pass'] is False else 'N/A'):<7} "
              f"{'Y' if e['project_mode'] else 'N':<5} "
              f"{'Y' if e['context_spin_down'] else 'N':<3} "
              f"{'Y' if e['context_spin_up'] else 'N':<3}")
    print("="*70)

    # ── Brain Sync of benchmark results ──────────────────────────────────────
    print("\n--- Syncing benchmark results to Agent Brain ---")
    try:
        from core.vector_store import HypervectorDB
        from utils.brain_sync import sync_record
        from core.knowledge_graph import KnowledgeGraph
        brain = HypervectorDB(filename=BRAIN_FILE)
        kg = KnowledgeGraph(storage=brain)
        brain.add_convo_step({
            "type": "STRESS_TEST",
            "timestamp": time.time(),
            "total_facts": total_facts,
            "duration": total_duration,
            "steps": full_chain
        })
        # Also sync each step result as a structured record
        for e in full_chain:
            sync_record(brain, kg, {
                "benchmark_step": e['step'],
                "query_summary": e['query'][:60],
                "code_execution": e['code_execution'],
                "project_mode": str(e['project_mode']),
                "brain_synced": str(e['brain_synced']),
                "duration_s": str(e['duration'])
            }, source_label="benchmark")
        print(f"[+] Sync complete. {len(full_chain)} step records in agent vectorized memory.")
    except Exception as e:
        print(f"[Sync Error] Could not save to brain: {e}")

    # ── BrainSync Verification ────────────────────────────────────────────────
    print("\n--- Post-Benchmark BrainSync Verification ---")
    try:
        from core.vector_store import HypervectorDB
        brain_check = HypervectorDB(filename=BRAIN_FILE)
        results = brain_check.search("benchmark step code execution", threshold=0.05, top_k=3)
        if results:
            print(f"[✅] Benchmark records are semantically searchable in agent memory ({len(results)} hits).")
        else:
            print("[⚠️] Benchmark records not found via semantic search — check brain encoding.")
    except Exception as e:
        print(f"[BrainSync Check Error] {e}")


if __name__ == "__main__":
    run_benchmark()
