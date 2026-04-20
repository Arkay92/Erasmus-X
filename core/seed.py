import os
import sys
import re
import time
import argparse
from openai import OpenAI
from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph
from utils.web_search import WebSearcher
from core import config, prompts

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

    def _safe_llm_call(self, prompt, system_prompt=None, max_tokens=150, temperature=0.1):
        """
        Robust wrapper for LLM calls with linear backoff.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=60.0 # Standard timeout for 2B
                )
                return response.choices[0].message.content
            except Exception as e:
                wait_time = (attempt + 1) * 5
                print(f" [!] LLM Issue (Attempt {attempt+1}/3): {e}")
                time.sleep(wait_time)
        return None

    def _load_questions(self, file_path):
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return re.findall(r"\d+\.\s*(.+)", content)

    def _extract_triplets_direct(self, text):
        """
        Direct high-speed triplet extraction from raw search data.
        """
        if not text or len(text) < 20: return False
        
        prompt = f"Extract exactly 3-5 knowledge triplets from the text below.\nOutput ONLY in the format: [FACT] subject | relation | object\n\nText: {text[:1000]}"
        raw = self._safe_llm_call(prompt, temperature=0)
        
        if raw and "[FACT]" in raw:
            facts = len(re.findall(r"\[FACT\]", raw))
            self.kg.extract_from_llm_response(raw)
            print(f" [>] Extracted {facts} symbolic relations.")
            return True
        return False

    def _process_single_question(self, q):
        """
        Handles search, vectorization, and symbolic induction for one question.
        """
        print(f" [>] Searching & Inducting: {q}")
        
        # 1. Search internet
        search_results = self.searcher.search(q)
        if not search_results:
            print(" [!] No internet context found.")
            return

        # 2. Vectorize context (Hypervector Induction)
        # Handle list of dicts (standard) or list of strings
        combined_text = ""
        if isinstance(search_results, list):
            for res in search_results:
                if isinstance(res, dict):
                    combined_text += f"{res.get('title', '')} {res.get('body', '')}\n"
                else:
                    combined_text += f"{str(res)}\n"
        else:
            combined_text = str(search_results)

        if len(combined_text) > 20:
            self.brain.add_document(f"Topic: {q} | Context: {combined_text[:2000]}")
            
            # 3. Direct Symbolic Extraction (Neurosymbolic Induction)
            self._extract_triplets_direct(combined_text)

    def run(self, limit=None):
        """
        Executes the seeding loop with high-throughput batching.
        """
        target_qs = self.questions[:limit] if limit else self.questions
        total = len(target_qs)
        start_time = time.time()
        
        print(f"\n--- Starting High-Throughput Seeding Engine (Model: 2B) ---")
        print(f"[*] Induction Goal: {total} topics")
        print(f"[*] Persistence: Sync to disk every 10 topics")
        
        for i, main_q in enumerate(target_qs, 1):
            # Calculate and display throughput
            elapsed = time.time() - start_time
            velocity = i / (elapsed / 60) if elapsed > 0 else 0
            
            print(f"\r[{i}/{total}] Inducting... (Velocity: {velocity:.1f} topics/min)", end="", flush=True)
            self._process_single_question(main_q)
            
            # Batch Persistence (Save every 10 items)
            if i % 10 == 0:
                self.brain.save()
        
        # Final sync
        self.brain.save()
        total_time = (time.time() - start_time) / 60
        print(f"\n\n--- Seeding Operation Complete ---")
        print(f"[+] Total Time: {total_time:.1f} minutes")
        print(f"[+] Average Speed: {total / total_time:.1f} topics/min")
        print(f"[+] Agent Brain synchronized to disk.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neurosymbolic Seeding Engine")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of questions to process")
    args = parser.parse_args()
    
    curriculum_path = "shards/questions/world_curriculum.md"
    engine = SeedingEngine(curriculum_path)
    
    if not engine.questions:
        print("No questions found in curriculum. Check the file path.")
        sys.exit(1)
        
    engine.run(limit=args.limit)
