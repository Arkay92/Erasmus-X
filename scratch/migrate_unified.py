import sys
import os
import torch

# Add root to path
sys.path.append(os.getcwd())

from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph

def migrate():
    print("--- Starting Unified Migration ---")
    brain = HypervectorDB()
    kg = KnowledgeGraph(storage=brain)
    
    print("\n--- Final Brain Status ---")
    print(f"Hypervectors: {len(brain.documents)}")
    print(f"Graph Nodes: {len(kg.graph.nodes)}")
    print(f"Convo Logs: {len(brain.convo_chain)}")
    
    brain.save()
    print("\n[+] All data synced to memories/agent_brain.pt")

if __name__ == "__main__":
    migrate()
