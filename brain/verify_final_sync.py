import time
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.vector_store import HypervectorDB

def verify_sync():
    test_file = "memories/test_final_sync.pt"
    if os.path.exists(test_file): os.remove(test_file)
    
    brain = HypervectorDB(filename=test_file)
    
    # Test step entry similar to benchmark
    entry = {
        "step": 1,
        "query": "Test query",
        "raw_output": "This is a test output response."
    }
    
    print("[*] Testing add_convo_step with valid data...")
    try:
        brain.add_convo_step(entry)
        print("[✅] Success")
    except Exception as e:
        print(f"[❌] Failed: {e}")

    # Test with missing field (simulating the bug)
    entry_buggy = {
        "step": 2,
        "query": "Buggy query"
        # raw_output is missing
    }
    
    print("[*] Testing add_convo_step with missing field (recovery test)...")
    try:
        brain.add_convo_step(entry_buggy)
        print("[✅] Success (Handled gracefully)")
    except Exception as e:
        print(f"[❌] Failed: {e}")

    # Verify searchability
    results = brain.search("test output response")
    if results:
        print(f"[✅] Search confirmed record in memory: {results[0][1]}")
    else:
        print("[❌] Search failed to find indexed record.")

    if os.path.exists(test_file): os.remove(test_file)

if __name__ == "__main__":
    verify_sync()
