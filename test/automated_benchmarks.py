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
    "Write a Python script to convert 100 degrees Fahrenheit to Celsius. [FILE: convert.py]"
]

def run_benchmark():
    print(f"--- Starting ULTIMATE Neurosymbolic Stress Test ---")
    
    start_time = time.time()
    
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
        
        # New: Execution Verification
        file_match = re.search(r"Saved (.+?) to scratch/", step_output)
        execution_status = "N/A"
        if file_match:
            filename = file_match.group(1).strip()
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            filepath = os.path.join(root_dir, 'scratch', filename)
            print(f"\n[*] Execution Verification: Running {filename}...")
            try:
                # Run the generated script
                run_res = subprocess.run(["python", filepath], capture_output=True, text=True, timeout=10)
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
            "output_len": len(step_output)
        }
        full_chain.append(entry)
        print(f"\n[+] Step complete in {entry['duration']}s | Search: {entry['search_triggered']} | Facts: {entry['facts_extracted']}")
        
        # Exit the fresh process
        process.stdin.write("exit\n")
        process.stdin.flush()
        process.terminate()
        
        # Small delay
        time.sleep(1)

    # Exit the agent
    print("\n--- Stress Test Complete. Exiting... ---")
    process.stdin.write("exit\n")
    process.stdin.flush()
    process.terminate()

    total_duration = time.time() - start_time
    total_facts = sum(e['facts_extracted'] for e in full_chain)
    search_ops = sum(1 for e in full_chain if e['search_triggered'])
    cache_hits = sum(1 for e in full_chain if e['is_cached'])
    code_success = sum(1 for e in full_chain if e['code_execution'] == "SUCCESS")
    code_total = sum(1 for e in full_chain if e['code_execution'] != "N/A")
    
    print("\n" + "="*50)
    print("ULTIMATE BENCHMARK SCORECARD")
    print(f"Total Time: {round(total_duration, 2)}s")
    print(f"Total Triplets Extracted: {total_facts}")
    print(f"Web Researches Performed: {search_ops}")
    print(f"Semantic Cache Hits: {cache_hits}")
    print(f"Autonomous Code Success: {code_success}/{code_total}")
    print("="*50)

    # Save Results (Unified Brain)
    print("\n--- Syncing benchmark results to Agent Brain ---")
    try:
        from core.vector_store import HypervectorDB
        brain = HypervectorDB(filename=BRAIN_FILE)
        brain.add_convo_step({
            "type": "STRESS_TEST",
            "timestamp": time.time(),
            "total_facts": total_facts,
            "duration": total_duration,
            "steps": full_chain
        })
        print(f"[+] Sync complete. Benchmark records are now part of the agent's vectorized memory.")
    except Exception as e:
        print(f"[Sync Error] Could not save to brain: {e}")
    
    print(f"\nBenchmark records are now part of the agent's vectorized memory within the binary Brain.")

if __name__ == "__main__":
    run_benchmark()
