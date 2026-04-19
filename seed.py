import sys
import os
import re
import time
import argparse

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph
from utils.web_search import WebSearcher
from openai import OpenAI
from core import config

class SeedingEngine:
    def __init__(self, questions_file):
        """
        Engine to bulk-populate the Neurosymbolic Brain by bypassing agent reasoning.
        """
        self.brain = HypervectorDB()
        self.kg = KnowledgeGraph(storage=self.brain)
        self.searcher = WebSearcher()
        self.client = OpenAI(base_url=config.API_BASE_URL, api_key=config.API_KEY)
        self.questions = self._load_questions(questions_file)

    def _load_questions(self, file_path):
        if not os.path.exists(file_path):
            print(f"Error: {file_path} not found.")
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Extract questions using regex for lines starting with "1. " or "201. " etc.
        questions = []
        for line in lines:
            match = re.match(r"^\d+\.\s+(.*)", line.strip())
            if match:
                questions.append(match.group(1))
        return questions

    def _extract_triplets_direct(self, text):
        """
        Direct high-speed triplet extraction from raw search data.
        Bypasses the Agent reasoning loop.
        """
        if not text: return
        
        prompt = f"Extract exactly 3-5 high-quality knowledge triplets from the text below.\nOutput ONLY in the format: [FACT] subject | relation | object\n\nText: {text[:1000]}"
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0
            )
            raw = response.choices[0].message.content
            self.kg.extract_from_llm_response(raw)
        except Exception as e:
            print(f" [!] Extraction failed: {e}")

    def run(self, limit=None):
        target_questions = self.questions[:limit] if limit else self.questions
        total = len(target_questions)
        
        print(f"--- Starting Neurosymbolic Seeding Engine ---")
        print(f"[*] Targeting {total} questions from curriculum.")
        
        for i, q in enumerate(target_questions):
            print(f"\n[{i+1}/{total}] Processing: {q}")
            
            # Step 1: Direct Web Search (Bypass LLM 'Skeptic' logic)
            print(" [>] Searching DuckDuckGo...")
            web_results = self.searcher.search(q)
            
            if web_results:
                # Step 2: Hypervectorization (Meta-summary)
                print(" [>] Vectorizing Internet Result...")
                self.brain.add_document(f"Question: {q} | Source: internet | Data: {web_results[:500]}")
                
                # Step 3: Symbolic Extraction (Direct to KG)
                print(" [>] Extracting Symbolic Relations...")
                self._extract_triplets_direct(web_results)
            else:
                print(" [!] No web results found. Skipping.")
                
            # Periodic Checkpoint
            if (i+1) % 5 == 0:
                print(f"\n[Checkpoint] Saving Agent Brain to disk...")
                self.brain.save()
            
            # Rate limit respect (DuckDuckGo can be sensitive)
            time.sleep(2)
            
        # Final Save
        self.brain.save()
        print("\n--- Seeding Operation Complete ---")
        print(f"[+] Agent Brain has been updated with results from {total} questions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neurosymbolic Seeding Engine")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of questions to process")
    args = parser.parse_args()
    
    # Path to curriculum
    curriculum_path = "questions/world_curriculum.md"
    
    engine = SeedingEngine(curriculum_path)
    if not engine.questions:
        print("No questions found in curriculum. Check the file path.")
        sys.exit(1)
        
    engine.run(limit=args.limit)
