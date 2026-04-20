import subprocess
import time
import json
import os
import re
import sys

# Ensure project root is in sys.path for direct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import config

# Test Suite Configuration
MAIN_SCRIPT = "main.py"
RESULTS_FILE = "memories/convo_chain.json"
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
    "Design and implement a complete Project: 'Planet Explorer'. This should be a multi-file application with a main entry point, a data module for JSON persistence to store planetary data, and a generator module for procedural planet names. Create a PLAN.md first."
]

def run_benchmark():
    print(f"--- Starting ULTIMATE Neurosymbolic Stress Test ---")
    
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
        print(f"\n[STRESS STEP {i+1}] Sending: {question}")
        
        # Send query
        process.stdin.write(question + "\n")
        process.stdin.flush()
        
        # Wait for Gemma's response
        step_output = wait_for_prompt(process)
        step_duration = time.time() - step_start
        
        # Extract response
        is_cached = "[Semantic Cache Hit]" in step_output
        
        # New: Execution Verification (Updated for Projects)
        file_match = re.search(r"Saved (.+?) to (.+?)/", step_output)
        execution_status = "N/A"
        if file_match:
            filename = file_match.group(1).strip()
            dir_name = file_match.group(2).strip()
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            
            if dir_name == "scratch":
                filepath = os.path.join(root_dir, 'scratch', filename)
            else:
                filepath = os.path.join(root_dir, 'scratch', dir_name, filename)
                
            print(f"\n[*] Execution Verification: Running {filename} in {dir_name}...")
            try:
                # Run the generated script
                run_res = subprocess.run(["python", filepath], capture_output=True, text=True, timeout=20)
                if run_res.returncode == 0:
                    execution_status = "SUCCESS"
                else:
                    msg = run_res.stderr.strip() or run_res.stdout.strip()
                    execution_status = f"FAILED ({msg[:40]}...)"
            except Exception as e:
                execution_status = f"ERROR ({str(e)})"
            print(f"[*] Execution Result: {execution_status}")

        entry = {
            "step": i + 1,
            "query": question,
            "duration": round(step_duration, 2),
            "is_cached": is_cached,
            "search_triggered": "[Headless Search]" in step_output,
            "facts_extracted": len(re.findall(r"\[FACT\].*", step_output)),
            "code_execution": execution_status,
            "project_mode": "Project Mode Detected" in step_output,
            "brain_synced": "BrainSync" in step_output,
            "output_len": len(step_output)
        }
        full_chain.append(entry)

        # Additional check: if project mode ran, verify directory was created
        if entry["project_mode"]:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            scratch_dirs = [d for d in os.listdir(os.path.join(root_dir, 'scratch'))
                            if d.startswith('project_')]
            proj_created = len(scratch_dirs) > 0
            entry["project_dir_created"] = proj_created
            print(f"[*] Project Dir Check: {'✅ Created' if proj_created else '❌ Missing'} ({scratch_dirs[-1] if scratch_dirs else 'none'})")
        else:
            entry["project_dir_created"] = None

        print(f"\n[+] Step {i+1} complete in {entry['duration']}s | "
              f"Cache: {entry['is_cached']} | Search: {entry['search_triggered']} | "
              f"Facts: {entry['facts_extracted']} | Code: {entry['code_execution']} | "
              f"Project: {entry['project_mode']} | BrainSync: {entry['brain_synced']}")
        
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
    code_total = sum(1 for e in full_chain if e['code_execution'] != "N/A")
    project_steps = [e for e in full_chain if e['project_mode']]
    proj_dirs_ok = sum(1 for e in project_steps if e.get('project_dir_created'))
    brain_syncs = sum(1 for e in full_chain if e['brain_synced'])

    print("\n" + "="*60)
    print("  ULTIMATE BENCHMARK SCORECARD")
    print("="*60)
    print(f"  Total Time          : {round(total_duration, 2)}s")
    print(f"  KG Triplets Extracted: {total_facts}")
    print(f"  Web Searches        : {search_ops}")
    print(f"  Semantic Cache Hits : {cache_hits}")
    print(f"  Code Execution Pass : {code_success}/{code_total}")
    print(f"  Project Dirs Created: {proj_dirs_ok}/{len(project_steps)}")
    print(f"  Brain Syncs         : {brain_syncs}")
    print("="*60)
    print("\n  Per-Step Summary:")
    print(f"  {'Step':<5} {'Time':>7}  {'Cache':<6} {'Search':<7} {'Facts':<6} {'Code':<10} {'Project':<8} {'Sync':<5}")
    print("  " + "-"*65)
    for e in full_chain:
        print(f"  {e['step']:<5} {e['duration']:>6.1f}s  "
              f"{'Y' if e['is_cached'] else 'N':<6} "
              f"{'Y' if e['search_triggered'] else 'N':<7} "
              f"{e['facts_extracted']:<6} "
              f"{e['code_execution'][:9]:<10} "
              f"{'Y' if e['project_mode'] else 'N':<8} "
              f"{'Y' if e['brain_synced'] else 'N':<5}")
    print("="*60)

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
