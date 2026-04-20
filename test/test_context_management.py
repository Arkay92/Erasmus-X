import os
import sys
import torch
import torchhd
from core.agent import NeurosymbolicAgent
from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph
from core.config import MAX_CONTEXT_HISTORY_CHARS
from unittest.mock import MagicMock

# Mock searcher
class MockSearcher:
    def search(self, query): return "Mock search results"

def test_context_management():
    print("\n" + "="*60)
    print("  NEUROSYMBOLIC AGENT -- CONTEXT MANAGEMENT TEST")
    print("="*60)

    # 1. Setup
    brain = HypervectorDB("memories/test_context.pt")
    # KnowledgeGraph takes the storage (brain) object as its first argument
    kg = KnowledgeGraph(brain)
    agent = NeurosymbolicAgent(brain, kg, MockSearcher())
    
    # 2. Force Spin-Down Trigger
    print("\n-- Step 1: Filling context with junk data --")
    # Add fake long messages to hit the 4000 char threshold
    long_msg = "A " * 2500 # 5000 chars total
    agent.messages = [
        {"role": "user", "content": long_msg},
        {"role": "assistant", "content": "I am processing a very long message history."}
    ]
    
    print(f"   Current context length: {agent._check_context_stability()} chars")
    
    # 3. Execution (Simulate a chat turn that should trigger spin-down)
    print("\n-- Step 2: Triggering chat turn (Should invoke Spin-Down) --")
    
    # Mock the LLM client to return a summary and then a response
    agent.client.chat.completions.create = MagicMock()
    
    # First call: Summary for spin-down
    # Second call: The actual answer (this will happen in a fresh session)
    mock_summary = MagicMock()
    mock_summary.message.content = "Summary: We are testing context resets."
    
    mock_answer = MagicMock()
    mock_answer.message.content = "I have reset my context. [FACT] test | status | passed"
    
    agent.client.chat.completions.create.side_effect = [mock_summary, mock_answer]
    
    user_input = "Can you continue from the previous session?"
    raw, clean = agent.chat(user_input)
    
    # 4. Assertions
    print("\n-- Step 3: Verifying Results --")
    
    # Verify spin-down saved to brain
    has_summary = any("[SESSION_STATE]" in doc for doc in brain.documents)
    print(f"   [*] Session state saved to Brain: {has_summary}")
    
    # Verify history was cleared (messages will contain the last Turn + assistant ans)
    # Actually chat() appends the new Turn. After spin-down, it should just be 1 turn.
    print(f"   [*] Active message history length: {len(agent.messages)}")
    
    # Verify semantic retrieval injected the summary
    # Check if a document with [SESSION_STATE] is in brain.documents
    mems = brain.search("[SESSION_STATE]", threshold=0.01)
    print(f"   [*] Found {len(mems)} session memories in Brain.")

    if has_summary and len(agent.messages) <= 2:
        print("\n[PASS] Context Management functional.")
    else:
        print("\n[FAIL] Context Management issues detected.")

    # Cleanup
    if os.path.exists("memories/test_context.pt"): os.remove("memories/test_context.pt")
    if os.path.exists("memories/test_context_kg.json"): os.remove("memories/test_context_kg.json")

if __name__ == "__main__":
    test_context_management()
