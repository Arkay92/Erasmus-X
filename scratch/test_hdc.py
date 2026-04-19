# Verification script for HDC HypervectorDB
import torch
import os
import sys

# Add the project root to sys.path to import from core
sys.path.append(os.getcwd())

from core.vector_store import HypervectorDB

def test():
    print("--- Initializing DB (should trigger migration if .json exists) ---")
    db = HypervectorDB()
    
    # Check if migration happened
    print(f"Number of documents in memory: {len(db.documents)}")
    
    # Add a new test document
    test_text = "The Erasmus Cell is an agentic AI system for research."
    db.add_document(test_text)
    
    # Search
    print("\n--- Searching for 'Erasmus' ---")
    results = db.search("Erasmus")
    for score, doc in results:
        print(f"[{score:.4f}] {doc[:100]}...")
        
    # Verify persistence
    print("\n--- Verifying persistence ---")
    if os.path.exists("memories/hypervector_memory.pt"):
        print("[+] Binary storage file created.")
    else:
        print("[-] Binary storage file NOT found.")

if __name__ == "__main__":
    test()
