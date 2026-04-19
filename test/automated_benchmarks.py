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

# 5 Levels of Ultimate Neurosymbolic Stress
TEST_QUESTIONS = [
    "Analyze the most recent financial results of NVIDIA (NVDA) and their primary stock catalyst.",
    "How does this compare to their previous quarterly guidance mentioned in our records?",
    "Extract a triplet graph of NVIDIA's partnerships and products mentioned in these reports.",
    "Given the partnerships we just mapped, which company is most vulnerable to an AI chip shortage?",
    "Summarize everything we've learned about the 'AI GPU Market' today and link it to our previous discussion on France's tech sector."
]

def run_benchmark():
    print(f"--- Starting ULTIMATE Neurosymbolic Stress Test ---")
    
    start_time = time.time()
    
    # Start the agent as a subprocess from the root
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

    full_chain = []
    
    def wait_for_prompt():
        """Reads output until the 'You:' prompt is found."""
        buffer = ""
        while True:
            char = process.stdout.read(1)
            if not char:
                break
            buffer += char
            # Print to console so we can see progress
            print(char, end="", flush=True)
            if buffer.endswith("You: "):
                break
        return buffer

    # Initial connection wait
    wait_for_prompt()
    
    for i, question in enumerate(TEST_QUESTIONS):
        step_start = time.time()
        print(f"\n[STRESS STEP {i+1}] Sending: {question}")
        
        # Send query
        process.stdin.write(question + "\n")
        process.stdin.flush()
        
        # Wait for Gemma's response
        step_output = wait_for_prompt()
        step_duration = time.time() - step_start
        
        # Extract response
        is_cached = "[Semantic Cache Hit]" in step_output
        entry = {
            "step": i + 1,
            "query": question,
            "duration": round(step_duration, 2),
            "is_cached": is_cached,
            "search_triggered": "[Headless Search]" in step_output,
            "facts_extracted": len(re.findall(r"\[FACT\].*", step_output)),
            "output_len": len(step_output)
        }
        full_chain.append(entry)
        print(f"\n[+] Step complete in {entry['duration']}s | Search: {entry['search_triggered']} | Facts: {entry['facts_extracted']}")
        
        # Small delay
        time.sleep(1)

    # Exit the agent
    print("\n--- Stress Test Complete. Exiting... ---")
    process.stdin.write("exit\n")
    process.stdin.flush()
    process.terminate()

    # Calculate Benchmark Score
    total_duration = time.time() - start_time
    total_facts = sum(e['facts_extracted'] for e in full_chain)
    search_ops = sum(1 for e in full_chain if e['search_triggered'])
    cache_hits = sum(1 for e in full_chain if e['is_cached'])
    
    print("\n" + "="*50)
    print("ULTIMATE BENCHMARK SCORECARD")
    print(f"Total Time: {round(total_duration, 2)}s")
    print(f"Total Triplets Extracted: {total_facts}")
    print(f"Web Researches Performed: {search_ops}")
    print(f"Semantic Cache Hits: {cache_hits}")
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
