import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph
from core.agent import NeurosymbolicAgent
from utils.web_search import WebSearcher
import torch

def test():
    brain = HypervectorDB(filename="memories/fast_lane_test.pt")
    kg = KnowledgeGraph(storage=brain)
    searcher = WebSearcher()
    agent = NeurosymbolicAgent(brain=brain, kg=kg, searcher=searcher)

    # 1. Test Recall Intent (Static)
    q1 = "Who is the CEO of Apple?"
    print(f"\n[Test Case 1] '{q1}'")
    agent.chat(q1)

    # 2. Test Search Intent (Dynamic)
    q2 = "What are the latest rumors about the iPhone 17?"
    print(f"\n[Test Case 2] '{q2}'")
    agent.chat(q2)

    # Clean up test brain
    if os.path.exists("memories/fast_lane_test.pt"):
        os.remove("memories/fast_lane_test.pt")

if __name__ == "__main__":
    test()
