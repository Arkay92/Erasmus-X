import unittest
import sys
import os
import shutil
from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestBrainKGIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_memories"
        os.makedirs(self.test_dir, exist_ok=True)
        self.brain_file = os.path.join(self.test_dir, "test_brain.pt")
        self.brain = HypervectorDB(filename=self.brain_file, dim=1024) # Smaller dimension for speed
        self.kg = KnowledgeGraph(storage=self.brain)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_fact_persistence_and_retrieval(self):
        # 1. Add document to brain
        self.brain.add_document("The project stack uses Next.js and Prisma.")
        
        # 2. Extract and Add fact to KG
        self.kg.add_triplet("project", "uses", "Next.js + Prisma")
        
        # 3. Search and Verify
        results = self.brain.search("Prisma", top_k=1)
        self.assertTrue(any("Prisma" in r[1] for r in results))
        
        facts = self.kg.get_related_facts("Next.js")
        self.assertTrue(any("next.js" in f.lower() for f in facts))

if __name__ == '__main__':
    unittest.main()
