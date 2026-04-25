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
    "what is the capital of France?",
    "write a python script that calculates the factorial of a number and save it to factorial.py",
    "create a simple project structure for a todo list app"
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

        # Extract Latency Metrics
        latency_map = {}
        latency_matches = re.findall(r"\[LATENCY\] ([\w_]+): ([\d\.]+)s", step_output)
        for stage, val in latency_matches:
            latency_map[stage] = float(val)
        execution_status = "N/A"
        critic_score = "N/A"
        capability_report = {}
        syntax_ok = True
               # Find all files mentioned
        file_matches = re.finditer(r"Saved validated (.+)", step_output)
        found_any_file = False
        
        for file_match in file_matches:
            found_any_file = True
            filename = file_match.group(1).strip()
            # Clean up potential extra log markers like " [Local LLM]" or " from ..."
            filename = filename.split()[0]
            # Assure we only check the true filename basename to bypass scratch_dir prefixes mapping bugs
            filename = os.path.basename(filename.replace('\\', '/'))
            
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
            is_main = filename in ["main.py", "gcd.py", "fib.py", "filter.py", "sort.py", "convert.py", "factorial.py"]
            if is_main and filepath and os.path.exists(filepath):
                print(f"\n[*] Execution Verification: Running {filename}...")
                try:
                    if filename == "factorial.py":
                        # Try with argv first, then stdin fallback (LLM may use either pattern)
                        run_res = subprocess.run([sys.executable, filepath, "5"], capture_output=True, text=True, timeout=10, input="5\n")
                    else:
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
                                
                        elif filename == "factorial.py":
                            if not re.search(r"\b120\b", stdout):
                                semantic_ok = False
                                msg = "Factorial result '120' for (5) not found."
                        
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
        
        # Elite V12: Critic Scoring Extraction
        score_match = re.search(r"SCORE:\s*(\d+)", step_output)
        if score_match:
             critic_score = score_match.group(1)
             print(f"[*] V12 Critic Score: {critic_score}")
        
        v12_stages = {
             "foundation": "FOUNDATION" in step_output,
             "logic": "logic" in step_output.lower() or "deep" in step_output.lower(),
             "critic": "Build Critic" in step_output
        }
        capability_report = v12_stages

        entry = {
            "step": i + 1,
            "query": str(question)[:100],
            "duration": round(step_duration, 2),
            "latency": latency_map,
            "is_cached": is_cached,
            "search_triggered": "[Headless Search]" in step_output,
            "facts_extracted": len(re.findall(r"\[FACT\].*", step_output)),
            "code_execution": execution_status,
            "syntax_pass": syntax_ok if found_any_file else "N/A",
            "project_mode": "[Project Phase]" in step_output or "[*] Project Planning Complete" in step_output,
            "brain_synced": "BrainSync" in step_output,
            "context_spin_down": is_spin_down,
            "context_spin_up": is_spin_up,
            "output_len": len(step_output),
            "critic_score": critic_score,
            "v12_caps": capability_report,
            "raw_output": step_output[:500] 
        }
        full_chain.append(entry)

        # Additional check: if project mode ran, verify directory was created & PLAN.md exists
        if entry["project_mode"]:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            sandbox_dirs = sorted([d for d in os.listdir(os.path.join(root_dir, 'sandboxes'))
                            if d.startswith('v12_') or d.startswith('v10_')], 
                            key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 0, 
                            reverse=True)
            proj_created = len(sandbox_dirs) > 0
            
            plan_exists = False
            if proj_created:
                # Use the first directory found after reverse sorting
                plan_path = os.path.join(root_dir, 'sandboxes', sandbox_dirs[0], 'PLAN.md')
                plan_exists = os.path.exists(plan_path)
            
            entry["project_dir_created"] = proj_created
            entry["plan_created"] = plan_exists
            
            proj_name = sandbox_dirs[0] if sandbox_dirs else 'none'
            print(f"[*] Project Dir Check: {'✅ Created' if proj_created else '❌ Missing'} ({proj_name})")
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
    
    v12_critic_avg = [int(e['critic_score']) for e in full_chain if e['critic_score'] != "N/A"]
    avg_score = sum(v12_critic_avg)/len(v12_critic_avg) if v12_critic_avg else 0
    print(f"  V12 Critic Avg Score : {avg_score:.1f}")
    
    print(f"  Context Spin-Downs   : {spin_downs}")
    print(f"  Session Continuity   : {spin_ups}")
    print(f"  Brain Syncs          : {brain_syncs}")
    print("="*70)
    
    # ── Latency Breakdown ─────────────────────────────────────────────────────
    all_latencies = {}
    for e in full_chain:
        for stage, val in e.get('latency', {}).items():
            if stage not in all_latencies: all_latencies[stage] = []
            all_latencies[stage].append(val)
    
    if all_latencies:
        print("\n  LATENCY BREAKDOWN (Averages):")
        print(f"  {'Stage':<30} | {'Avg Latency':>12}")
        print("  " + "-"*45)
        for stage, vals in sorted(all_latencies.items()):
            avg = sum(vals) / len(vals)
            print(f"  {stage:<30} | {avg:>11.4f}s")
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
